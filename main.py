from traceback_with_variables import Format, ColorSchemes, global_print_exc, printing_exc, LoggerAsFile
from bs4 import BeautifulSoup
import random
import string
from typing import Union
from multiprocessing.pool import ThreadPool
import re
import time
import coloredlogs
import verboselogs
from logging.handlers import RotatingFileHandler
import sys
import httpx

import settings
import solvers

fmterr = Format(
    max_value_str_len=5000,
    color_scheme=ColorSchemes.common,
    max_exc_str_len=5000,
)
global_print_exc(fmt=fmterr)

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
# todo: this is possibly wrong
pattern_df_id = re.compile(r'href\|max\|([0-9a-f]+)\|navigator\|if\|cookieEnabled\|cookie\|(\w+)\|else\|again\|in\|cookies\|your\|browser', re.MULTILINE)

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
        if not (pstring and pstring.string == "Please enable JavaScript and Cookies in your browser."):
            return False
        script = soup.find("script")
        if not script:
            return False
        if not script.string.startswith('setTimeout(eval(function(p,a,c,k,e,d)'):
            return False

        self.logger.verbose("lolz asks to complete df_id task")

        match = pattern_df_id.search(script.string)
        self.logger.debug("df_id %s", str(match.group(1)))
        self.session.cookies.set(domain="." + settings.lolzdomain,
                                 name=match.group(2),
                                 value=match.group(1))
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
            if self.current_proxy_number >= len(self.proxy_pool):
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

    def solvecontest(self, thrid) -> bool:  # return whether we were successful
        solver = solvers.SolverTurnsile(self)

        if not solver.on_before_request(thrid):
            return False

        contestResp = self.makerequest("GET",
                                       settings.lolzUrl + "threads/" + str(thrid) + "/",
                                       retries=3,
                                       timeout=12.05,
                                       checkforjs=True)
        if contestResp is None:
            return False

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

        if not solver.solve(contestSoup):
            return False

        self.logger.info("waiting for participation...")
        response = solver.participate(csrf)
        if response is None:
            return False

        if "error" in response and response["error"][0] == 'Вы не можете участвовать в своём розыгрыше.':
            self.blacklist.add(thrid)

        if "_redirectStatus" in response and response["_redirectStatus"] == 'ok':
            solver.on_success(response)
            return True
        else:
            solver.on_failure(response)
            return False

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

            self.logger.notice("participating in %s thread id %d", contestName, thrid)

            if self.solvecontest(thrid):
                self.logger.success("successfully participated in %s thread id %s", contestName, thrid)

            time.sleep(settings.switch_time)
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
        self.session.headers.update({"User-Agent": parameters[1]["User-Agent"]})
        for key, value in parameters[1]["cookies"].items():
            self.session.cookies.set(
                domain="." + settings.lolzdomain,
                name=key,
                value=value)

        if settings.proxy_type == 2:
            self.proxy_pool = parameters[1]["proxy_pool"]
            if len(self.proxy_pool) == 0:
                raise Exception("%s has empty proxy_pool" % self.username)

        self.blacklist = set()

        # kinda a hack to loop trough proxies because python doesn't have static variables
        self.current_proxy_number = -1  # self.changeproxy adds one to this number
        self.changeproxy()  # set initital proxy
        self.session.cookies.set(domain=settings.lolzdomain, name='xf_viewedContestsHidden', value='1')
        self.session.cookies.set(domain=settings.lolzdomain, name='xf_feed_custom_order', value='post_date')
        self.session.cookies.set(domain=settings.lolzdomain, name='xf_logged_in', value='1')


def main():
    with ThreadPool(processes=len(settings.users)) as pool:
        userlist = [User(u) for u in list(settings.users.items())]
        pool.map(User.work, userlist)
        print("lul done?")


if __name__ == '__main__':
    main()
