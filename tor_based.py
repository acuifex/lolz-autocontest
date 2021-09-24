# noinspection PyUnresolvedReferences
from traceback_with_variables import activate_by_import
from bs4 import BeautifulSoup
import random
import string
import eventlet
from typing import Tuple
from urllib.parse import quote
from multiprocessing.pool import ThreadPool
import base64
import io
from PIL import Image
import re
import json
import time
import coloredlogs
import verboselogs
from logging.handlers import RotatingFileHandler
from enum import Enum
import sys

# import requests
requests = eventlet.import_patched('requests')

lolzdomain = "lolz.guru"
lolzUrl = "https://" + lolzdomain + "/"

f = open('settings.json')
data = json.load(f)
users = data["users"]
torproxy = data["use_tor"]
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

fileHandler = RotatingFileHandler("lolzautocontest.log", maxBytes=1024*1024*4, backupCount=10)  # rotate every 4 megs
fileHandler.setFormatter(logfmt)

pattern_csrf = re.compile(r'_csrfToken:\s*\"(.*)\",', re.MULTILINE)
pattern_captcha_dot = re.compile(r'XenForo.ClickCaptcha.dotSize\s*=\s*(\d+);', re.MULTILINE)
pattern_captcha_img = re.compile(r'XenForo.ClickCaptcha.imgData\s*=\s*"([A-Za-z0-9+/=]+)";', re.MULTILINE)

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
        if not torproxy:
            return
        randstr = ''.join(random.choices(string.ascii_lowercase, k=5))
        self.logger.verbose("changing proxy to %s", randstr)
        self.session.proxies = {'http': 'socks5://{}@localhost:9050'.format(randstr + ":" + self.temp_name),
                                'https': 'socks5://{}@localhost:9050'.format(randstr + ":" + self.temp_name)}

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
                            .find("h3", class_="title").find("span").contents[0]
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
                                    dot = int(pattern_captcha_dot.search(scriptcaptcha.string).group(1))
                                    if dot != 20:
                                        self.logger.critical("dotsize isn't 20 but instead is %d", dot)
                                    img = pattern_captcha_img.search(scriptcaptcha.string).group(1)
                                    x, y, confidence = solve(img)
                                    self.logger.debug("solved x,y: %d,%d confidence: %.2f", x, y, confidence)

                                    self.logger.debug("waiting for participation...")
                                    response = self.participate(str(thrid), x, y, captchahash, csrf)
                                    if response is not None:
                                        if "error" in response and \
                                                response["error"][0] == 'Вы не можете участвовать в своём розыгрыше.':
                                            blacklist.add(thrid)

                                        if "_redirectStatus" in response and response["_redirectStatus"] == 'ok':
                                            self.logger.success("successfully participated in %s thread id %s",
                                                                contestname,
                                                                thrid)
                                        else:
                                            self.logger.error("didn't participate. img: %s", img)
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

    def __init__(self, cookies):
        self.session = requests.session()
        self.temp_name = cookies[0]

        self.logger = verboselogs.VerboseLogger(self.temp_name)
        self.logger.addHandler(fileHandler)
        # self.logger.addHandler(consoleHandler)
        coloredlogs.install(fmt=logfmtstr, stream=sys.stdout, level_styles=level_styles,
                            milliseconds=True, level='DEBUG', logger=self.logger)
        self.logger.debug("cookies %s", cookies)
        if torproxy:
            self.session.proxies = {'http': 'socks5://{}@localhost:9050'.format("asdasd:" + cookies[0]),
                                    'https': 'socks5://{}@localhost:9050'.format("asdasd:" + cookies[0])}
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0"})

        for key, value in cookies[1].items():
            if key == "User-Agent":
                self.session.headers.update({"User-Agent": value})
            else:
                # these are strict:
                # df_id is with dot
                # xf_user and xf_tfa_trust are without dots
                self.session.cookies.set_cookie(requests.cookies.create_cookie(
                    domain=("." if key == "df_id" else "")+lolzdomain,
                    name=key,
                    value=value))
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=lolzdomain, name='xf_viewedContestsHidden', value='1'))
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=lolzdomain, name='xf_feed_custom_order', value='post_date'))
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=lolzdomain, name='xf_logged_in', value='1'))

    def participate(self, threadid: str, x: int, y: int, captchahash: str, csrf: str):
        response = self.makerequest(Methods.post, lolzUrl + "threads/" + threadid + "/participate", data={
                    'captcha_hash': captchahash,
                    'captcha_type': "ClickCaptcha",
                    'x': x,
                    'y': y,
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


# mask of a circle. i know that this is suboptimal
# non gray are required while gray are "optional" if you can say so
isgray_mask = (
    (True, True, True, True, True, True, True, True, True, True, False, True, True, True, True, True, True, True, True, True, True),
    (True, True, True, True, True, True, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True),
    (True, True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True),
    (True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True, True),
    (True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True, True),
    (True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True),
    (True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True, True),
    (True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True, True),
    (True, True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True),
    (True, True, True, True, True, True, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True),
    (True, True, True, True, True, True, True, True, True, True, False, True, True, True, True, True, True, True, True, True, True)
)
total_grays = sum(x.count(True) for x in isgray_mask)
total_reds = sum(x.count(False) for x in isgray_mask)


def solve(captchab64: str) -> Tuple[int, int, float]:
    img = Image.open(io.BytesIO(base64.b64decode(captchab64)))
    pixels = img.load()
    bestx = besty = 0
    bestconfidence = 0
    for tiley in range(0, img.size[1], 20):
        for tilex in range(0, img.size[0], 20):
            gray_count = 0  # counts the amount of correct color outside the circle
            red_count = 0  # counts the amount of correct color inside the circle
            junk_in_red_count = 0  # counts the amount of non red and non gray inside the circle
            for x in range(21):
                for y in range(21):
                    if tiley + y >= 200 or tilex + x >= 240:  # if out of bounds, just assume it's correct
                        if isgray_mask[x][y]:
                            gray_count += 1
                        else:
                            red_count += 1  # this is probably bad, this will create up to 2 incorrect pixels!!! fight me about it
                        continue

                    if isgray_mask[x][y]:
                        gray_count += 1 if 0xff not in pixels[x+tilex, y+tiley] else 0
                    else:
                        red_count += 1 if 0xff in pixels[x + tilex, y + tiley] else 0
                        junk_in_red_count += 1 if 0xff not in pixels[x + tilex, y + tiley] and pixels[x + tilex, y + tiley] != (0x40, 0x40, 0x40) else 0
            confidence = abs(junk_in_red_count*0.3 + red_count-total_reds/2) * -1 + gray_count * 1.6
            # 0.3, -1 and 1.6 are the weights, negative weight means smaller the number - better
            if bestconfidence < confidence:
                bestconfidence = confidence
                bestx, besty = tilex, tiley
    return int(bestx/20), int(besty/20), bestconfidence


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
