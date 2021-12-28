import urllib3.exceptions
from traceback_with_variables import Format, ColorSchemes, global_print_exc, printing_exc, LoggerAsFile
from bs4 import BeautifulSoup
import random
import string
import eventlet
from typing import Union
from urllib.parse import quote
from multiprocessing.pool import ThreadPool
import base64
import re
import json
import time
import coloredlogs
import verboselogs
from logging.handlers import RotatingFileHandler
import sys
import os

import settings
import solvers

fmterr = Format(
    max_value_str_len=-1,
    color_scheme=ColorSchemes.common,
    max_exc_str_len=-1,
)
global_print_exc(fmt=fmterr)

# import requests
requests = eventlet.import_patched('requests')

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


# consoleHandler = logging.StreamHandler(sys.stdout)
# consoleHandler.setFormatter(logfmt)


class User:
    def makerequest(self,
                    method: str,
                    url,
                    checkforjs=False,
                    timeout_eventlet=None,
                    retries=1,
                    **kwargs) -> Union[requests.Response, None]:
        for i in range(0, retries):
            timeoutobj = eventlet.Timeout(timeout_eventlet)
            try:
                resp = self.session.request(method, url, **kwargs)
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
                except urllib3.exceptions.SSLError as e:
                    self.logger.warning("%s SSLError (timeout?): %s", url, str(e))
                time.sleep(settings.low_time)
                continue
            else:
                timeoutobj.cancel()
                try:
                    resp.raise_for_status()
                except requests.HTTPError:
                    self.logger.warning("%s Lolz down with %s status", url, resp.status_code)
                    time.sleep(settings.low_time)
                    continue

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
        if noscript:
            pstring = noscript.find("p")
            if pstring and pstring.string == "Please enable JavaScript and Cookies in your browser.":
                self.logger.verbose("lolz asks to complete js task")

                resp = self.makerequest("GET",
                                        settings.lolzUrl + "process-qv9ypsgmv9.js",
                                        timeout_eventlet=15, timeout=12.05, retries=3)
                if resp is None:
                    return True

                df_idvalue = extractdf_id(resp.text)
                self.logger.debug("PoW answer %s", str(df_idvalue))
                self.session.cookies.set_cookie(requests.cookies.create_cookie(domain="." + settings.lolzdomain,
                                                                               name='df_id',
                                                                               value=df_idvalue.decode("ascii")))
                return True  # should retry
        return False

    def changeproxy(self):
        if not settings.proxy_enabled:
            return

        if settings.proxy_type == 1:
            randstr = ''.join(random.choices(string.ascii_lowercase, k=5))
            self.logger.verbose("changing proxy to %s", randstr)
            self.session.proxies = {'http': 'socks5://{}@localhost:9050'.format(randstr + ":" + self.username),
                                    'https': 'socks5://{}@localhost:9050'.format(randstr + ":" + self.username)}
        elif settings.proxy_type == 2:  # these are the moments i wish python had switch cases
            self.current_proxy_number += 1
            if self.current_proxy_number >= self.proxy_pool_len:
                self.current_proxy_number = 0
            proxy = self.proxy_pool[self.current_proxy_number]
            self.logger.verbose("changing proxy to %s index %d", proxy, self.current_proxy_number)
            self.session.proxies = {'http': proxy,
                                    'https': proxy}
            pass
        elif settings.proxy_type == 3:  # TODO: implement global pool
            pass

    def solvepage(self) -> bool:  # return whether we found any contests or not
        found_contest = False
        contestListResp = self.makerequest("GET",
                                           settings.lolzUrl + "forums/contests/",
                                           timeout_eventlet=15,
                                           timeout=12.05,
                                           retries=3,
                                           checkforjs=True)
        if contestListResp is None:
            return False

        contestlistsoup = BeautifulSoup(contestListResp.text, "html.parser")

        contestList = contestlistsoup.find("div", class_="discussionListItems")
        if contestList is None:
            self.logger.critical("%s", contestlistsoup.text)
            self.logger.critical("couldn't find discussionListItems. Exiting...")
            raise RuntimeError

        threadsList = []

        stickyThreads = contestList.find("div", class_="stickyThreads")
        if stickyThreads:
            threadsList.extend(stickyThreads.findChildren(recursive=False))

        latestThreads = contestList.find("div", class_="latestThreads")
        if latestThreads:
            threadsList.extend(latestThreads.findChildren(recursive=False))

        if len(threadsList) == 0:
            return False

        self.logger.notice("detected %d contests", len(threadsList))
        for contestDiv in threadsList:
            thrid = int(contestDiv.get('id').split('-')[1])

            if thrid in self.blacklist:
                continue
            found_contest = True
            contestName = contestDiv.find("div", class_="discussionListItem--Wrapper") \
                .find("a", class_="listBlock main PreviewTooltip") \
                .find("h3", class_="title").find("span", class_="spanTitle").contents[0]

            self.logger.notice("participating in %s thread id %d", contestName, thrid)

            contestResp = self.makerequest("GET",
                                           settings.lolzUrl + "threads/" + str(thrid),
                                           retries=3,
                                           timeout_eventlet=15,
                                           timeout=12.05,
                                           checkforjs=True)
            if contestResp is None:
                continue

            contestSoup = BeautifulSoup(contestResp.text, "html.parser")

            script = contestSoup.find("script", text=pattern_csrf)
            if script is None:
                self.logger.error("%s", contestSoup.text)
                self.logger.error("no csrf token!")
                continue

            csrf = pattern_csrf.search(script.string).group(1)
            if not csrf:
                self.logger.critical("%s", contestSoup.text)
                self.logger.critical("csrf token is empty. dead cookies? FIXME!!!")
                continue
            self.logger.debug("csrf: %s", str(csrf))

            divcaptcha = contestSoup.find("div", class_="captchaBlock")
            if divcaptcha is None:
                self.logger.warning("Couldn't get captchaBlock. Lag or contest is over?")
                continue

            captchaType = divcaptcha.find("input", attrs={"name": "captcha_type"}).get("value")

            solver = self.solvers.get(captchaType)
            if solver is None:
                self.logger.critical("%s doesn't have a solver. Exiting.", captchaType)
                raise RuntimeError

            self.logger.verbose("for %s using solver %s", captchaType, type(solver).__name__)

            participateParams = solver.solve(divcaptcha)
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
                self.logger.error("didn't participate: %s", str(response))
            self.logger.debug("%s", str(response))
        return found_contest

    def work(self):
        with printing_exc(file_=LoggerAsFile(self.logger), fmt=fmterr):
            starttime = time.time()
            found_contest = 0

            self.logger.debug("work cookies %s", str(self.session.cookies))
            self.logger.debug("work headers %s", str(self.session.headers))
            while True:
                try:
                    self.logger.notice("ip: %s", self.session.get("https://httpbin.org/ip", timeout=6.05).json()["origin"])
                except requests.Timeout:
                    self.changeproxy()
                    time.sleep(settings.low_time)
                    continue
                break

            while True:
                self.logger.info("loop at %.2f seconds", time.time() - starttime)

                if self.solvepage():
                    found_contest = settings.found_count

                if found_contest > 0:
                    found_contest -= 1
                    time.sleep(settings.low_time)
                else:
                    time.sleep(settings.high_time)

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
                    domain="." + settings.lolzdomain,
                    name=key,
                    value=value))
            if key in ["xf_user", "xf_tfa_trust"]:
                self.session.cookies.set_cookie(requests.cookies.create_cookie(
                    domain=settings.lolzdomain,
                    name=key,
                    value=value))
            if key == "proxy_pool":
                self.proxy_pool = value
                self.proxy_pool_len = len(self.proxy_pool)  # cpu cycle savings

        if settings.proxy_enabled and settings.proxy_type == 2:  # dumbass user check
            if not hasattr(self, 'proxy_pool'):
                raise Exception("%s doesn't have proxy_pool set" % self.username)
            if self.proxy_pool_len == 0:
                raise Exception("%s has empty proxy_pool" % self.username)

        self.blacklist = set()

        self.solvers = {
            "Slider2Captcha": solvers.SolverSlider2(self),
            "ClickCaptcha": solvers.SolverHalfCircle(self),
        }

        # kinda a hack to loop trough proxies because python doesn't have static variables
        self.current_proxy_number = -1  # self.changeproxy adds one to this number
        self.changeproxy()  # set initital proxy
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=settings.lolzdomain, name='xf_viewedContestsHidden', value='1'))
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=settings.lolzdomain, name='xf_feed_custom_order', value='post_date'))
        self.session.cookies.set_cookie(
            requests.cookies.create_cookie(domain=settings.lolzdomain, name='xf_logged_in', value='1'))

    def participate(self, threadid: str, csrf: str, data: dict):
        # https://stackoverflow.com/questions/6005066/adding-dictionaries-together-python
        response = self.makerequest("POST", settings.lolzUrl + "threads/" + threadid + "/participate",
                                    data={**data, **{
                                        '_xfRequestUri': quote("/threads/" + threadid + "/"),
                                        '_xfNoRedirect': 1,
                                        '_xfToken': csrf,
                                        '_xfResponseType': "json",
                                    }}, timeout_eventlet=15, timeout=12.05, retries=3, checkforjs=True)

        if response is None:
            return None

        try:
            parsed = json.loads(response.text)
            self.logger.debug("parsed")
        except ValueError:
            self.logger.critical("SOMETHING BAD 2!!\n%s", response.text)
            raise

        return parsed


def extractdf_id(html):
    return base64.b64decode(
        re.sub(r"'\+'", "", re.search(r"var _0x2ef7=\[[A-Za-z0-9+/=',]*','([A-Za-z0-9+/=']*?)'];", html).group(1)))


def main():
    if not os.path.exists(settings.imagesDir):
        os.makedirs(settings.imagesDir)
    with ThreadPool(processes=len(settings.users)) as pool:
        userlist = [User(u) for u in list(settings.users.items())]
        pool.map(User.work, userlist)
        print("lul done?")


if __name__ == '__main__':
    main()
