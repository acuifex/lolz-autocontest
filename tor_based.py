from traceback_with_variables import activate_by_import
from bs4 import BeautifulSoup
import random
import string
import eventlet
# import requests
requests = eventlet.import_patched('requests')
from urllib.parse import quote
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from multiprocessing.pool import ThreadPool
import base64
import re
import json
import time
import logging, coloredlogs, verboselogs
from logging.handlers import RotatingFileHandler
from enum import Enum
import sys

lolzdomain = "lolz.guru"
lolzUrl = "https://" + lolzdomain + "/"

##################################################### РЕДАКТИРУЕМ ТОЛЬКО ТО ЧТО СНИЗУ
#####################################################
users = {
    "tomas": {  # Назвать аккаунт в одно слово
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0",  # ОБЯЗАТЕЛЬНО МЕНЯЕМ НА СВОЙ!!!!
        "xf_user": "136698%6969420CcBaDCoDe696969",  # Твоя кука входа
        "df_id": "696969abcdef",  # Айди сессии
        "xf_tfa_trust": "asdgdfhkuo253qz-"  # Может не быть этой куки при некоторых случаях. не волнуемся
    },
    # "donate": {
    #     "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0",
    #     "xf_user": "136698%6969420CcBaDCoDe696969",
    #     "df_id": "696969abcdef",
    #     "xf_tfa_trust": "asdgdfhkuo253qz-"
    # },
}

torproxy = True

found_count = 8  # Если нашелся розыгрыш чекать розыгрыши каждые low_time секунд found_count раз
low_time = 5  # Чекать каждые low_time Секунд если нашелся новый розыгрыш
high_time = 20  # Чекать каждые high_time секунд если нету новых розыгрышей
#####################################################
##################################################### РЕДАКТИРУЕМ ТОЛЬКО ТО ЧТО СВЕРХУ




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

# consoleHandler = logging.StreamHandler(sys.stdout)
# consoleHandler.setFormatter(logfmt)

class Methods(Enum):
    post = 'POST'
    get = 'GET'

class user:
    def makeRequest(self, method: Methods, url, checkforjs=False, timeout_eventlet=None, retries=1, data=None, json=None, **kwargs):
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
                    self.changeProxy()
                except eventlet.Timeout:
                    self.logger.warning("%s eventlet timeout", url)
                    self.changeProxy()
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
                if checkforjs and self.checkForJsAndFix(soup):
                    self.logger.debug("%s had JS PoW", url)
                    continue  # we have js gayness
                return soup  # everything good
        else:
            return None  # failed after x retries


    def checkForJsAndFix(self, soup):
        if (hueta := soup.find("noscript")) and (hueta := hueta.find("p")) \
                and hueta.string == "Please enable JavaScript and Cookies in your browser.":
            self.logger.verbose("lolz asks to complete js task")

            resp = self.makeRequest(Methods.get, lolzUrl + "process-qv9ypsgmv9.js", timeout_eventlet=15, timeout=12.05, retries=3)
            if resp is None:
                return True

            koki = dealWithGayStuff(resp.text)
            self.logger.debug("PoW ansfer %s", str(koki))
            self.session.cookies.set_cookie(
                requests.cookies.create_cookie(domain="." + lolzdomain, name='df_id', value=koki.decode("ascii")))
            return True  # should retry
        return False

    def changeProxy(self):
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
                self.changeProxy()
                time.sleep(low_time)
                continue
            break
        while True:
            self.logger.info("loop at %.2f seconds", time.time() - starttime)

            contestlistsoup = self.makeRequest(Methods.get, lolzUrl + "forums/contests/", timeout_eventlet=15, timeout=12.05, retries=3, checkforjs=True)
            if contestlistsoup is not None:
                contestlist = contestlistsoup.find("div", class_="latestThreads _insertLoadedContent")
                if contestlist:
                    self.logger.notice("detected %d contests", len(contestlist.findChildren(recursive=False)))
                    for gay in contestlist.findChildren(recursive=False):
                        thrid = int(gay.get('id').split('-')[1])
                        if thrid in blacklist:
                            continue
                        found_contest = found_count
                        contestname = gay.find("div", class_="discussionListItem--Wrapper").find("a", class_="listBlock main PreviewTooltip").find("h3", class_="title").find("span").contents[0]
                        self.logger.notice("parcipitating in %s threadid %d",
                                            contestname, thrid)

                        contestsoup = self.makeRequest(Methods.get, lolzUrl + "threads/" + str(thrid), retries=3, timeout_eventlet=15, timeout=12.05, checkforjs=True)
                        if contestsoup is not None:
                            pattern_csrf = re.compile(r'_csrfToken:\s*\"(.*)\",', re.MULTILINE)
                            script = contestsoup.find("script", text=pattern_csrf)
                            if script:
                                csrf = pattern_csrf.search(script.string).group(1)
                                if not csrf:
                                    self.logger.critical("csrf token is empty. dead cookies? FIXME!!!")
                                    self.logger.critical("%s", contestsoup.text)
                                self.logger.debug("csrf: %s", str(csrf))

                                cookieresp = self.requestCaptchaCookie(csrf, str(thrid))
                                if cookieresp is not None:
                                    cookie, uuid = cookieresp
                                    self.logger.debug("cookie, uuid: %s %s" + str(cookie) + str(uuid))
                                    self.logger.debug("waiting for predict...")
                                    x, y = predictPosition(csrf, cookie, thrid)
                                    # x = x + random.randint(-5, 5)
                                    self.logger.debug("predicted position x: %d y: %d", x, y)

                                    # time.sleep(5)

                                    self.logger.debug("waiting for parcipitation...")
                                    response = self.parcipitate(str(thrid), x, uuid, csrf)
                                    if response is not None:
                                        if "error" in response and response["error"][0] == 'Вы не можете участвовать в своём розыгрыше.':
                                            blacklist.add(thrid)

                                        if "_redirectStatus" in response and response["_redirectStatus"] == 'ok':
                                            self.logger.success("succesefully parcipitated in %s threadid %s", contestname, thrid)

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
                self.session.cookies.set_cookie(
                    requests.cookies.create_cookie(domain=lolzdomain, name=key, value=value))
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=lolzdomain, name='xf_viewedContestsHidden', value='1'))
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=lolzdomain, name='xf_feed_custom_order', value='post_date'))
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=lolzdomain, name='xf_logged_in', value='1'))

    def requestCaptchaCookie(self, csrf: str,
                             threadid: str):  # def requestCaptchaCookie(userid: str, xsrf: str, threadid: str):

        response = self.makeRequest(Methods.post, lolzUrl + "threads/contest/slider-captcha", data={
                'username': quote(csrf.split(",")[0]),
                'xsrf': csrf.split(",")[2][::-1],
                'topics': threadid,
                '_xfRequestUri': quote("/threads/" + threadid + "/"),
                '_xfNoRedirect': 1,
                '_xfToken': csrf,
                '_xfResponseType': "json",
            }, timeout_eventlet=15, timeout=12.05, retries=3, checkforjs=True)

        if response is None:
            return None

        try:
            # parsed = response.json()
            parsed = json.loads(response.text)
            self.logger.debug("parsed")
        except ValueError:
            self.logger.critical("SOMETHING BAD!!\n%s", response.text)
            raise
        return parsed["cookie"], parsed["uuid"]

    def parcipitate(self, threadid: str, solvedX: int, uuid: str, csrf: str):
        payload = {"success": True, "proofs": {"solvetUUID": uuid, "solvetVector": solvedX}}
        base64enc = base64.b64encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
        base64conv = base64enc.decode('utf-8')
        self.logger.debug("b64: %s", base64conv)
        payloadEncryption = fad(xorstring(base64conv, 35), 'e')

        response = self.makeRequest(Methods.post, lolzUrl + "threads/" + threadid + "/participate", data={
                    'p': payloadEncryption,
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


def fad(str, type):
    if type == 'd':
        return base64.b64decode(re.sub(r"%([0-9A-F]{2})", lambda x: chr(int(x.group(1), 16)), quote(str)))

    if type == 'e':
        return base64.b64encode(
            re.sub(r"%([0-9A-F]{2})", lambda x: chr(int(x.group(1), 16)), quote(str)).encode('utf-8'))


def xorstring(str, value):
    out = ""
    for i in str:
        out += chr(ord(i) ^ value)
    return out


def predictPosition(csrf: str, msg: str,
                    threadid: int):  # def predictPosition(userid: str, xsrf: str, msg: str, threadid):
    xsrf = csrf.split(",")[2][::-1]
    salt = xsrf[8:16]
    iv = bytes(xsrf[0:16].encode("ascii"))

    key = PBKDF2(csrf.split(",")[0], bytes(salt.encode("ascii")), 16, 10000)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    flow = cipher.decrypt(fad(xorstring(base64.b64decode(msg).decode('ascii'), 35), 'd')).decode('utf-8').strip()

    # print(Fore.LIGHTBLACK_EX + "flow, threadid: " + str(flow) + str(threadid) + Fore.RESET)
    x = int(flow[-7:]) - threadid
    y = x

    x = x + 10
    y = y + 9 * 2  # that.y = ctx_cc.y + that.options.sliderR * 2
    return x, y


def dealWithGayStuff(html):
    return base64.b64decode(
        re.sub(r"'\+'", "", re.search(r"var _0x2ef7=\[[A-Za-z0-9+/=',]*','([A-Za-z0-9+/=']*?)'\];", html).group(1)))


def main():
    with ThreadPool(processes=len(users)) as pool:
        userList = [user(u) for u in list(users.items())]
        pool.map(user.work, userList)
        print("lul done?")


if __name__ == '__main__':
    main()

# tomas waiting for list...
# tomas detected 30 contests
# parcipitating in 100-ка на ход ноги threadid 2159490
# tomas csrf:
# tomas HAS UNCAUGHT EXEPTION list index out of range FIX IT DAMMIT!
# lul done?