# noinspection PyUnresolvedReferences
from traceback_with_variables import activate_by_import
from bs4 import BeautifulSoup
import random
import string
import eventlet
from typing import Tuple, Union
from urllib.parse import quote
from multiprocessing.pool import ThreadPool
import base64
import io
from PIL import Image, ImageFilter
import re
import json
import time
import coloredlogs
import verboselogs
from logging.handlers import RotatingFileHandler
from enum import Enum
import sys
import numpy as np
import struct
import mmh3

# import requests
requests = eventlet.import_patched('requests')

lolzdomain = "lolz.guru"
lolzUrl = "https://" + lolzdomain + "/"

f = open('settings.json')
data = json.load(f)
users = data["users"]
proxy_enabled = data["use_proxy"]
save_error_images = data["save_error_images"]
proxy_type = data["proxy_type"]
found_count = data["found_count"]
low_time = data["low_time"]
high_time = data["high_time"]
f.close()

level_styles = {'debug': {'color': 8},
                'info': {},
                'warning': {'color': 11},
                'error': {'color': 'red'},
                'critical': {'bold': True, 'color': 'red'},

                'spam': {'color': 'green', 'faint': True},
                'verbose': {'color': 'blue'},
                'notice': {'color': 'magenta'},
                'success': {'bold': True, 'color': 'green'},
                }

logfmtstr = "%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s"
logfmt = coloredlogs.ColoredFormatter(logfmtstr, level_styles=level_styles)

fileHandler = RotatingFileHandler("lolzautocontest.log", maxBytes=1024*1024*4, backupCount=10, encoding='utf-8')  # rotate every 4 megs
fileHandler.setFormatter(logfmt)

pattern_csrf = re.compile(r'_csrfToken:\s*\"(.*)\",', re.MULTILINE)
pattern_captcha_sid = re.compile(r"sid\s*:\s*'([0-9a-f]{32})'", re.MULTILINE)

# consoleHandler = logging.StreamHandler(sys.stdout)
# consoleHandler.setFormatter(logfmt)


class Methods(Enum):
    post = 'POST'
    get = 'GET'


class User:
    def makerequest(self,
                    method: Methods,
                    url,
                    checkforjs=False,
                    timeout_eventlet=None,
                    retries=1,
                    data=None,
                    json=None,
                    **kwargs):
        for i in range(0, retries):
            timeoutobj = eventlet.Timeout(timeout_eventlet)
            try:
                resp = self.session.request(method.value, url, data=data, json=json, **kwargs)
            except:
                timeoutobj.cancel()
                try:
                    raise
                except requests.Timeout:
                    self.logger.warning("%s requests timeout", url)
                    self.changeproxy()
                except eventlet.Timeout:
                    self.logger.warning("%s eventlet timeout", url)
                    self.changeproxy()
                except requests.ConnectionError:
                    self.logger.warning("%s ConnectionError", url)
                time.sleep(low_time)
                continue
            else:
                timeoutobj.cancel()
                try:
                    resp.raise_for_status()
                except requests.HTTPError:
                    self.logger.warning("%s Lolz down with %s status", url, resp.status_code)
                    time.sleep(low_time)
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                if checkforjs and self.checkforjsandfix(soup):
                    self.logger.debug("%s had JS PoW", url)
                    continue  # we have js gayness

                # TODO: this is a dirty dirty hack, remove this when you're gonna refactor and allways return resp
                if not checkforjs:
                    return resp
                return soup  # everything good
        else:
            return None  # failed after x retries

    def checkforjsandfix(self, soup):
        noscript = soup.find("noscript")
        if noscript:
            pstring = noscript.find("p")
            if pstring and pstring.string == "Please enable JavaScript and Cookies in your browser.":
                self.logger.verbose("lolz asks to complete js task")

                resp = self.makerequest(Methods.get,
                                        lolzUrl + "process-qv9ypsgmv9.js",
                                        timeout_eventlet=15, timeout=12.05, retries=3)
                if resp is None:
                    return True

                df_idvalue = extractdf_id(resp.text)
                self.logger.debug("PoW answer %s", str(df_idvalue))
                self.session.cookies.set_cookie(requests.cookies.create_cookie(domain="." + lolzdomain,
                                                                               name='df_id',
                                                                               value=df_idvalue.decode("ascii")))
                return True  # should retry
        return False

    def changeproxy(self):
        if not proxy_enabled:
            return

        if proxy_type == 1:
            randstr = ''.join(random.choices(string.ascii_lowercase, k=5))
            self.logger.verbose("changing proxy to %s", randstr)
            self.session.proxies = {'http': 'socks5://{}@localhost:9050'.format(randstr + ":" + self.username),
                                    'https': 'socks5://{}@localhost:9050'.format(randstr + ":" + self.username)}
        elif proxy_type == 2:  # these are the moments i wish python had switch cases
            self.current_proxy_number += 1
            if self.current_proxy_number >= self.proxy_pool_len:
                self.current_proxy_number = 0
            proxy = self.proxy_pool[self.current_proxy_number]
            self.logger.verbose("changing proxy to %s index %d", proxy, self.current_proxy_number)
            self.session.proxies = {'http': proxy,
                                    'https': proxy}
            pass
        elif proxy_type == 3:  # TODO: implement global pool
            pass

    def work(self):
        blacklist = set()
        starttime = time.time()
        found_contest = 0

        self.logger.debug("work cookies %s", str(self.session.cookies))
        self.logger.debug("work headers %s", str(self.session.headers))
        while True:
            try:
                self.logger.notice("ip: %s", self.session.get("https://httpbin.org/ip", timeout=6.05).json()["origin"])
            except requests.Timeout:
                self.changeproxy()
                time.sleep(low_time)
                continue
            break
        while True:
            self.logger.info("loop at %.2f seconds", time.time() - starttime)

            contestlistsoup = self.makerequest(Methods.get,
                                               lolzUrl + "forums/contests/",
                                               timeout_eventlet=15,
                                               timeout=12.05,
                                               retries=3,
                                               checkforjs=True)
            if contestlistsoup is not None:
                contestlist = contestlistsoup.find("div", class_="latestThreads _insertLoadedContent")
                if contestlist:
                    self.logger.notice("detected %d contests", len(contestlist.findChildren(recursive=False)))
                    for gay in contestlist.findChildren(recursive=False):
                        thrid = int(gay.get('id').split('-')[1])
                        if thrid in blacklist:
                            continue
                        found_contest = found_count
                        contestname = gay.find("div", class_="discussionListItem--Wrapper")\
                            .find("a", class_="listBlock main PreviewTooltip")\
                            .find("h3", class_="title").find("span", class_="spanTitle").contents[0]
                        self.logger.notice("participating in %s thread id %d", contestname, thrid)

                        contestsoup = self.makerequest(Methods.get,
                                                       lolzUrl + "threads/" + str(thrid),
                                                       retries=3,
                                                       timeout_eventlet=15,
                                                       timeout=12.05,
                                                       checkforjs=True)
                        if contestsoup is not None:
                            script = contestsoup.find("script", text=pattern_csrf)
                            if script:
                                csrf = pattern_csrf.search(script.string).group(1)
                                if not csrf:
                                    self.logger.critical("csrf token is empty. dead cookies? FIXME!!!")
                                    self.logger.critical("%s", contestsoup.text)
                                self.logger.debug("csrf: %s", str(csrf))
                                divcaptcha = contestsoup.find("div", class_="captchaBlock")
                                if not divcaptcha:
                                    self.logger.warning("it just so happened that this contest just ended between requesting the list and requesting the page")
                                else:
                                    captchahash = divcaptcha.find("input", attrs={"name": "captcha_hash"}).get("value")
                                    scriptcaptcha = divcaptcha.find("script")
                                    self.logger.debug("sid: %s", pattern_captcha_sid.search(scriptcaptcha.string).group(1))
                                    sid = int(pattern_captcha_sid.search(scriptcaptcha.string).group(1), 16).to_bytes(16, byteorder="big")
                                    captcharesponse = self.requestcaptcha(sid)
                                    if captcharesponse:
                                        y, captcha, puzzle, datahash = captcharesponse

                                        self.logger.debug("hash: %d", datahash)
                                        x, diff = solve(captcha, puzzle, y)
                                        self.logger.debug("solved x,y: %d,%d diff: %.2f", x, y, diff)
                                        solutionresponse = self.sendsolution(sid, datahash, x)
                                        if solutionresponse is not None:

                                            self.logger.debug("waiting for participation... %d", solutionresponse)
                                            response = self.participate(str(thrid), captchahash, csrf)
                                            if response is not None:
                                                if "error" in response and \
                                                        response["error"][0] == 'Вы не можете участвовать в своём розыгрыше.':
                                                    blacklist.add(thrid)

                                                if "_redirectStatus" in response and response["_redirectStatus"] == 'ok':
                                                    self.logger.success("successfully participated in %s thread id %s",
                                                                        contestname,
                                                                        thrid)
                                                else:
                                                    if save_error_images:
                                                        with open(str(datahash) + '_captcha.png', 'wb') as file:
                                                            file.write(captcha)
                                                        with open(str(datahash) + '_puzzle.png', 'wb') as file:
                                                            file.write(puzzle)
                                                    self.logger.error("didn't participate: %s", str(response))
                                                self.logger.debug("%s", str(response))
                            else:
                                self.logger.error("%s", contestsoup.text)
                                self.logger.error("no csrf token!")
                                continue
            if found_contest > 0:
                found_contest -= 1
                time.sleep(low_time)
            else:
                time.sleep(high_time)

    def __init__(self, parameters):
        self.session = requests.session()
        self.username = parameters[0]

        self.logger = verboselogs.VerboseLogger(self.username)
        self.logger.addHandler(fileHandler)
        # self.logger.addHandler(consoleHandler)
        coloredlogs.install(fmt=logfmtstr, stream=sys.stdout, level_styles=level_styles,
                            milliseconds=True, level='DEBUG', logger=self.logger)
        self.logger.debug("user parameters %s", parameters)

        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0"})
        for key, value in parameters[1].items():
            if key == "User-Agent":
                self.session.headers.update({"User-Agent": value})
            if key == "df_id":
                self.session.cookies.set_cookie(requests.cookies.create_cookie(
                    domain="."+lolzdomain,
                    name=key,
                    value=value))
            if key in ["xf_user", "xf_tfa_trust"]:
                self.session.cookies.set_cookie(requests.cookies.create_cookie(
                    domain=lolzdomain,
                    name=key,
                    value=value))
            if key == "proxy_pool":
                self.proxy_pool = value
                self.proxy_pool_len = len(self.proxy_pool)  # cpu cycle savings

        if proxy_enabled and proxy_type == 2:  # dumbass user check
            if not hasattr(self, 'proxy_pool'):
                raise Exception("%s doesn't have proxy_pool set" % self.username)
            if self.proxy_pool_len == 0:
                raise Exception("%s has empty proxy_pool" % self.username)
        # kinda a hack to loop trough proxies because python doesn't have static variables
        self.current_proxy_number = -1  # self.changeproxy adds one to this number
        self.changeproxy()  # set initital proxy
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=lolzdomain, name='xf_viewedContestsHidden', value='1'))
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=lolzdomain, name='xf_feed_custom_order', value='post_date'))
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=lolzdomain, name='xf_logged_in', value='1'))

    def requestcaptcha(self, sid: bytes) -> Union[Tuple[int, bytes, bytes, int], None]:
        response = self.makerequest(Methods.post, "https://captcha." + lolzdomain + "/captcha", headers={'referer': "https://lolz.guru/",
                                                                                                         'origin': "https://lolz.guru"}, cookies={}, data=sid,
                                    timeout_eventlet=15, timeout=12.05, retries=3, checkforjs=False)

        if response is None:
            return None

        datahash = mmh3.hash(response.content[0x15:], 0xf0e8, False)

        # struct: hack_me_if_you_can\n, short, payload
        key = struct.unpack("H", bytes(response.content[0x13:0x13 + 2]))[0] ^ 0x5c37
        decrypted = applyencryption(key, bytes(response.content[0x13 + 2:]))

        # struct: 0x00, int1, int2, int3, png of size int1, png of size int2
        imgsize1, imgsize2, y = struct.unpack("III", decrypted[1:1 + struct.calcsize("III")])
        return y, decrypted[13:13 + imgsize1], decrypted[13 + imgsize1:13 + imgsize1 + imgsize2], datahash

    def sendsolution(self, sid: bytes, datahash: int, x: int) -> Union[int, None]:

        # works without captcha start -> captcha end path but doesn't work without start -> capctha start
        # ehh whatever it'll look more realistic on the server anyway
        # TODO: make like an actual random path generator so it's even more realistic
        tmp = bytes.fromhex("0288000000AD0100000288000000AE0100000287000000AE0100000287000000AF0100000287000000B00100000287000000B10100000287000000B20100000286000000B30100000286000000B40100000286000000B50100000286000000B60100000286000000B70100000286000000B80100000286000000B90100000286000000BA0100000286000000BB0100000286000000BC0100000286000000BD0100000286000000BE0100000286000000BF0100000285000000C00100000285000000C10100000285000000C20100000285000000C30100000285000000C40100000284000000C40100000284000000C50100000283000000C60100000283000000C70100000283000000C80100000283000000C90100000282000000C90100000282000000CA0100000282000000CB0100000281000000CB0100000281000000CC0100000281000000CD0100000281000000CE0100000281000000CF0100000281000000D00100000281000000D10100000281000000D20100000281000000D30100000281000000D40100000281000000D50100000281000000D60100000281000000D70100000282000000D70100000282000000D80100000282000000D90100000282000000DA0100000281000000DA0100000281000000DB0100000280000000DB010000027F000000DB010000027E000000DB010000027E000000DC010000027D000000DC010000027D000000DD010000027C000000DD010000027B000000DD010000027A000000DD0100000279000000DE0100000278000000DE0100000277000000DE0100000277000000DF010000")
        tmp += struct.pack("<Bii", 0x00, 119, 481)
        for i in range(x):
            tmp += struct.pack("<Bii", 0x02, 119+i, 481)
        tmp += struct.pack("<Bii", 0x01, 119+x, 481)
        encrypted = applyencryption(datahash&0xffff, tmp)

        requestdata = b"hack_me_if_you_can\n" + sid + encrypted

        response = self.makerequest(Methods.post, "https://captcha." + lolzdomain + "/captcha", headers={'referer': "https://lolz.guru/",
                                                                                                         'origin': "https://lolz.guru"}, cookies={}, data=requestdata,
                                    timeout_eventlet=15, timeout=12.05, retries=3, checkforjs=False)

        if response is None:
            return None

        return int.from_bytes(response.content, byteorder='little')

    def participate(self, threadid: str, captchahash: str, csrf: str):
        response = self.makerequest(Methods.post, lolzUrl + "threads/" + threadid + "/participate", data={
                    'captcha_hash': captchahash,
                    'captcha_type': "Slider2Captcha",
                    '_xfRequestUri': quote("/threads/" + threadid + "/"),
                    '_xfNoRedirect': 1,
                    '_xfToken': csrf,
                    '_xfResponseType': "json",
                }, timeout_eventlet=15, timeout=12.05, retries=3, checkforjs=True)

        if response is None:
            return None

        try:
            parsed = json.loads(response.text)
            self.logger.debug("parsed")
        except ValueError:
            self.logger.critical("SOMETHING BAD 2!!\n%s", response.text)
            raise

        return parsed


def applyencryption(key: int, data: bytes) -> bytes:
    out = io.BytesIO()
    for i in data:
        out.write((i ^ (key & 0xff)).to_bytes(1, byteorder='big'))
        uVar3 = (key >> 1) & 0x7fff
        uVar6 = key & 1
        key = uVar3 ^ 0xffffb400
        if uVar6 == 0:
            key = uVar3
    out.seek(0)
    return out.read()

# todo: check if y is within 0 to 200-30
def solve(captcha: bytes, puzzle: bytes, y: int):
    img = Image.open(io.BytesIO(captcha))
    img = img.filter(ImageFilter.Kernel(size=(3,3),kernel=(
        0,1,0,
        1,-4,1,
        0,1,0
    ), scale=1))
    img = img.crop((0, y, img.size[0], y+30))
    captcha = np.asarray(img).sum(axis=0)

    # img.show()
    #
    # w = np.asarray(img)
    # w = w.sum(axis=0)
    # w = w * ( 255 / w.max())
    # w = w.reshape((1, 300, 3))
    # img2 = Image.fromarray(w.astype(np.uint8))
    # img2.show()

    puzzle = np.asarray(Image.open(io.BytesIO(puzzle)).convert("RGB")).sum(axis=0)
    bestx = 0
    leastdiff = 2147483647  # basically maxint, 999999 would work too but meh
    # difflist = []
    for x in range(0, captcha.shape[0]-30):
        diffarr = np.average(np.abs(np.subtract(captcha[x:x + 30], puzzle, dtype="int64")), 1)
        diff = np.mean(diffarr)
        # difflist.append(diff)
        if diff < leastdiff:
            bestx = x
            leastdiff = diff
        pass

    # asfd = np.array(difflist)
    # asfd = asfd - asfd.min()
    # asfd = asfd * ( 255 / asfd.max())
    # asfd = asfd.reshape((1, 270))
    # img2 = Image.fromarray(asfd.astype(np.uint8))
    # img2.show()

    return bestx, leastdiff


def extractdf_id(html):
    return base64.b64decode(
        re.sub(r"'\+'", "", re.search(r"var _0x2ef7=\[[A-Za-z0-9+/=',]*','([A-Za-z0-9+/=']*?)'];", html).group(1)))


def main():
    with ThreadPool(processes=len(users)) as pool:
        userlist = [User(u) for u in list(users.items())]
        pool.map(User.work, userlist)
        print("lul done?")


if __name__ == '__main__':
    main()
