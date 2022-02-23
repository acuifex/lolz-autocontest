import urllib3.exceptions
from traceback_with_variables import Format, ColorSchemes, global_print_exc, printing_exc, LoggerAsFile
from bs4 import BeautifulSoup
import random
import string
from typing import Union
from urllib.parse import quote
from multiprocessing.pool import ThreadPool
import re
import json
import time
import coloredlogs
import verboselogs
from logging.handlers import RotatingFileHandler
import sys
import os
from Crypto.Cipher import AES

import settings
import solvers

fmterr = Format(
    max_value_str_len=-1,
    color_scheme=ColorSchemes.common,
    max_exc_str_len=-1,
)
global_print_exc(fmt=fmterr)

import httpx

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

# rotate every 4 megs
fileHandler = RotatingFileHandler("lolzautocontest.log", maxBytes=1024 * 1024 * 4, backupCount=10, encoding='utf-8')
fileHandler.setFormatter(logfmt)

pattern_csrf = re.compile(r'_csrfToken:\s*\"(.*)\",', re.MULTILINE)
pattern_df_id = re.compile(r'document\.cookie\s*=\s*"([^="]+)="\s*\+\s*toHex\(slowAES\.decrypt\(toNumbers\(\"([0-9a-f]{32})\"\)', re.MULTILINE)


# consoleHandler = logging.StreamHandler(sys.stdout)
# consoleHandler.setFormatter(logfmt)


class User:
    def makerequest(self,
                    method: str,
                    url,
                    checkforjs=False,
                    retries=1,
                    **kwargs) -> Union[httpx.Response, None]:
        for i in range(0, retries):
            try:
                resp = self.session.request(method, url, **kwargs)
                resp.raise_for_status()
            except httpx.TimeoutException as e:
                self.logger.warning("%s timeout", e.request.url)
                self.changeproxy()
                time.sleep(settings.low_time)
            except httpx.ProxyError as e:
                self.logger.warning("%s proxy error (%s)", e.request.url, str(e))
                self.changeproxy()
                time.sleep(settings.low_time)
            except httpx.TransportError as e:
                self.logger.warning("%s TransportError (%s)", e.request.url, str(e))
                self.changeproxy()
                time.sleep(settings.low_time)
            except httpx.HTTPStatusError as e:
                self.logger.warning("%s responded with %s status", e.request.url, e.response.status_code)
                time.sleep(settings.low_time)
            else:
                if checkforjs:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    if self.checkforjsandfix(soup):
                        self.logger.debug("%s had JS PoW", url)
                        continue  # we have js gayness

                return resp
        else:
            return None  # failed after x retries

    def checkforjsandfix(self, soup):
        noscript = soup.find("noscript")
        if not noscript:
            return False
        pstring = noscript.find("p")
        if not (pstring and pstring.string == "Oops! Please enable JavaScript and Cookies in your browser."):
            return False
        script = soup.find_all("script")
        if not script:
            return False
        if not (script[1].string.startswith('var _0xe1a2=["\\x70\\x75\\x73\\x68","\\x72\\x65\\x70\\x6C\\x61\\x63\\x65","\\x6C\\x65\\x6E\\x67\\x74\\x68","\\x63\\x6F\\x6E\\x73\\x74\\x72\\x75\\x63\\x74\\x6F\\x72","","\\x30","\\x74\\x6F\\x4C\\x6F\\x77\\x65\\x72\\x43\\x61\\x73\\x65"];function ')
                and script[0].get("src") == '/aes.js'):
            return False

        self.logger.verbose("lolz asks to complete aes task")

        match = pattern_df_id.search(script[1].string)
        cipher = AES.new(bytearray.fromhex("e9df592a0909bfa5fcff1ce7958e598b"), AES.MODE_CBC,
                         bytearray.fromhex("5d10aa76f4aed1bdf3dbb302e8863d52"))
        value = cipher.decrypt(bytearray.fromhex(match.group(2))).hex()
        self.logger.debug("PoW answer %s", str(value))
        self.session.cookies.set(domain="." + settings.lolzdomain,
                                 name=match.group(1),
                                 value=value)
        return True  # should retry

    def changeproxy(self):
        if settings.proxy_type == 0:
            return

        newProxy = {}
        if settings.proxy_type == 1:
            randstr = ''.join(random.choices(string.ascii_lowercase, k=5))
            self.logger.verbose("changing proxy to %s", randstr)
            newProxy = {'all://': 'socks5://{}@localhost:9050'.format(randstr + ":" + self.username)}
        elif settings.proxy_type == 2:  # these are the moments i wish python had switch cases
            self.current_proxy_number += 1
            if self.current_proxy_number >= self.proxy_pool_len:
                self.current_proxy_number = 0
            proxy = self.proxy_pool[self.current_proxy_number]
            self.logger.verbose("changing proxy to %s index %d", proxy, self.current_proxy_number)
            newProxy = {'all://': proxy}
            pass
        elif settings.proxy_type == 3:  # TODO: implement global pool
            pass

        # hack to change proxies with httpx
        newSession = httpx.Client(http2=True, proxies=newProxy)
        newSession.headers = self.session.headers
        newSession.cookies = self.session.cookies
        self.session = newSession

    def solvepage(self) -> bool:  # return whether we found any contests or not
        found_contest = False
        contestListResp = self.makerequest("GET",
                                           settings.lolzUrl + "forums/contests/",
                                           timeout=12.05,
                                           retries=3,
                                           checkforjs=True)
        if contestListResp is None:
            return False

        contestlistsoup = BeautifulSoup(contestListResp.text, "html.parser")

        contestList = contestlistsoup.find("div", class_="discussionListItems")
        if contestList is None:
            self.logger.critical("%s", str(contestlistsoup))
            raise RuntimeError("couldn't find discussionListItems.")

        threadsList = []

        stickyThreads = contestList.find("div", class_="stickyThreads")
        if stickyThreads:
            threadsList.extend(stickyThreads.findChildren(recursive=False))

        latestThreads = contestList.find("div", class_="latestThreads")
        if latestThreads:
            threadsList.extend(latestThreads.findChildren(recursive=False))

        if len(threadsList) == 0:
            return False
        # TODO: make threadsList a list of threadids instead of html objects
        # also remove all blacklisted threadids before we get to this point
        self.logger.notice("detected %d contests", len(threadsList))
        for contestDiv in threadsList:
            thrid = int(contestDiv.get('id').split('-')[1])

            if thrid in self.blacklist or thrid in settings.ExpireBlacklist:
                continue
            found_contest = True
            contestName = contestDiv.find("div", class_="discussionListItem--Wrapper") \
                .find("a", class_="listBlock main PreviewTooltip") \
                .find("h3", class_="title").find("span", class_="spanTitle").contents[0]
            # this is not very nice but should avoid the bug with not sleeping when skipping for some reason
            time.sleep(settings.switch_time)

            self.logger.notice("participating in %s thread id %d", contestName, thrid)

            # TODO: stuff bellow probably should get it's own function

            contestResp = self.makerequest("GET",
                                           settings.lolzUrl + "threads/" + str(thrid) + "/",
                                           retries=3,
                                           timeout=12.05,
                                           checkforjs=True)
            if contestResp is None:
                continue

            contestSoup = BeautifulSoup(contestResp.text, "html.parser")

            script = contestSoup.find("script", text=pattern_csrf)
            if script is None:
                self.logger.error("%s", str(contestSoup))
                raise RuntimeError("no csrf token!")

            csrf = pattern_csrf.search(script.string).group(1)
            if not csrf:
                self.logger.critical("%s", str(contestSoup))
                raise RuntimeError("csrf token is empty. likely bad cookies")
            self.logger.debug("csrf: %s", str(csrf))

            divcaptcha = contestSoup.find("div", class_="captchaBlock")
            if divcaptcha is None:
                self.logger.warning("Couldn't get captchaBlock. Lag or contest is over?")
                continue

            captchatypeobj = divcaptcha.find("input", attrs={"name": "captcha_type"})

            if captchatypeobj is None:
                self.logger.warning("captcha_type not found. adding to blacklist...")
                self.blacklist.add(thrid)
                continue

            captchaType = captchatypeobj.get("value")

            solver = self.solvers.get(captchaType)
            if solver is None:
                raise RuntimeError(f"\"{captchaType}\" doesn't have a solver.")

            self.logger.verbose("for %s using solver %s", captchaType, type(solver).__name__)

            participateParams = solver.solve(divcaptcha, id=thrid)
            if participateParams is None:
                continue

            self.logger.debug("waiting for participation...")
            response = self.participate(str(thrid), csrf, participateParams)
            if response is None:
                continue

            if "error" in response and response["error"][0] == 'Вы не можете участвовать в своём розыгрыше.':
                self.blacklist.add(thrid)

            if "_redirectStatus" in response and response["_redirectStatus"] == 'ok':
                self.logger.success("successfully participated in %s thread id %s", contestName, thrid)
            else:
                if captchaType == "AnswerCaptcha": # TODO: this is kina a hack
                    self.logger.error("%s has wrong answer", thrid)
                    settings.ExpireBlacklist[thrid] = time.time() + 300000
                self.logger.error("didn't participate: %s", str(response))
            self.logger.debug("%s", str(response))
        return found_contest

    def work(self):
        with printing_exc(file_=LoggerAsFile(self.logger), fmt=fmterr):
            starttime = time.time()
            found_contest = 0

            self.logger.debug("work cookies %s", str(self.session.cookies))
            self.logger.debug("work headers %s", str(self.session.headers))
            ip = self.makerequest("GET", "https://httpbin.org/ip", timeout=12.05, retries=30)
            if ip:
                self.logger.notice("ip: %s", ip.json()["origin"])
            else:
                raise RuntimeError("Wasn't able to reach httpbin.org in 30 tries. Check your proxies and your internet connection")
            while True:
                cur_time = time.time()
                # remove old entries
                settings.ExpireBlacklist = {k: v for k, v in settings.ExpireBlacklist.items() if v > cur_time}
                self.logger.info("loop at %.2f seconds (blacklist size %d)", cur_time - starttime,
                                 len(settings.ExpireBlacklist))

                if self.solvepage():
                    found_contest = settings.found_count

                if found_contest > 0:
                    found_contest -= 1
                    time.sleep(settings.low_time)
                else:
                    time.sleep(settings.high_time)

    def __init__(self, parameters):
        self.session = httpx.Client(http2=True)
        self.username = parameters[0]

        self.logger = verboselogs.VerboseLogger(self.username)
        self.logger.addHandler(fileHandler)
        # self.logger.addHandler(consoleHandler)
        coloredlogs.install(fmt=logfmtstr, stream=sys.stdout, level_styles=level_styles,
                            milliseconds=True, level='DEBUG', logger=self.logger)
        self.logger.debug("user parameters %s", parameters)

        self.monitor_dims = (parameters[1]["monitor_size_x"], parameters[1]["monitor_size_y"])
        self.session.headers.update({"User-Agent": parameters[1]["User-Agent"]})
        for key, value in parameters[1]["cookies"].items():
            self.session.cookies.set(
                domain="." + settings.lolzdomain,
                name=key,
                value=value)

        if settings.proxy_type == 2:
            self.proxy_pool = parameters[1]["proxy_pool"]
            self.proxy_pool_len = len(self.proxy_pool)  # cpu cycle savings
            if self.proxy_pool_len == 0:
                raise Exception("%s has empty proxy_pool" % self.username)

        self.blacklist = set()

        self.solvers = {
            "Slider2Captcha": solvers.SolverSlider2(self),
            "ClickCaptcha": solvers.SolverHalfCircle(self),
            "AnswerCaptcha": solvers.SolverAnswers(self),
        }

        # kinda a hack to loop trough proxies because python doesn't have static variables
        self.current_proxy_number = -1  # self.changeproxy adds one to this number
        self.changeproxy()  # set initital proxy
        self.session.cookies.set(domain=settings.lolzdomain, name='xf_viewedContestsHidden', value='1')
        self.session.cookies.set(domain=settings.lolzdomain, name='xf_feed_custom_order', value='post_date')
        self.session.cookies.set(domain=settings.lolzdomain, name='xf_logged_in', value='1')

    def participate(self, threadid: str, csrf: str, data: dict):
        # https://stackoverflow.com/questions/6005066/adding-dictionaries-together-python
        response = self.makerequest("POST", settings.lolzUrl + "threads/" + threadid + "/participate",
                                    data={**data, **{
                                        '_xfRequestUri': quote("/threads/" + threadid + "/"),
                                        '_xfNoRedirect': 1,
                                        '_xfToken': csrf,
                                        '_xfResponseType': "json",
                                    }}, timeout=12.05, retries=3, checkforjs=True)

        if response is None:
            return None

        try:
            parsed = json.loads(response.text)
            self.logger.debug("parsed")
        except ValueError:
            self.logger.critical("SOMETHING BAD 2!!\n%s", response.text)
            raise

        return parsed


def main():
    if not os.path.exists(settings.imagesDir):
        os.makedirs(settings.imagesDir)
    with ThreadPool(processes=len(settings.users)) as pool:
        userlist = [User(u) for u in list(settings.users.items())]
        pool.map(User.work, userlist)
        print("lul done?")


if __name__ == '__main__':
    main()
