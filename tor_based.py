from traceback_with_variables import activate_by_import
from bs4 import BeautifulSoup
import random
import string
import eventlet
# import requests
requests = eventlet.import_patched('requests')
from urllib.parse import quote
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

pattern_csrf = re.compile(r'_csrfToken:\s*\"(.*)\",', re.MULTILINE)

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
                            script = contestsoup.find("script", text=pattern_csrf)
                            if script:
                                csrf = pattern_csrf.search(script.string).group(1)
                                if not csrf:
                                    self.logger.critical("csrf token is empty. dead cookies? FIXME!!!")
                                    self.logger.critical("%s", contestsoup.text)
                                self.logger.debug("csrf: %s", str(csrf))
                                block = contestsoup.find("div", class_="captchaBlock")
                                captchahash = block.find("input", name="captcha_question_hash").get("value")
                                svg = block.find("div", class_="captchaImg").find("svg")\
                                    .find("path", class_="iZQNWyob_0").get("d").partition(",")[0]
                                answer = solvesvg(svg)
                                self.logger.debug("solved svg: %s", answer)

                                self.logger.debug("waiting for parcipitation...")
                                response = self.parcipitate(str(thrid), answer, captchahash, csrf)
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

    def parcipitate(self, threadid: str, answer: str, captchahash: str, csrf: str):

        response = self.makeRequest(Methods.post, lolzUrl + "threads/" + threadid + "/participate", data={
                    'captcha_question_answer': answer,
                    'captcha_question_hash': captchahash,
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

translation_dict = {
"L0.00 0.00Q13.99 0.00 13.99 26.65L13.99 26.65Q13.99 53.30 0.00 53.30L0.00 53.30Q-13.96 53.30 -13.96 26.65L-13.96 26.65Q-13.96 0.00 0.00 0.00ZM-7.03 39.16L-7.03 39.16L5.84 9.81Q3.80 4.96 -0.07 4.96L-0.07 4.96Q-8.05 4.96 -8.05 26.65L-8.05 26.65Q-8.05 34.03 -7.03 39.16ZM7.07 14.17L-5.84 43.42Q-3.87 48.34 0.00 48.34L0.00 48.34Q8.09 48.34 8.09 26.58L8.09 26.58Q8.09 19.37 7.07 14.17L7.07 14.17": "0",
"L-5.90 0.00L-5.90 -43.07Q-8.61 -41.24 -13.46 -39.20L-13.46 -39.20L-13.46 -45.00Q-7.84 -47.08 -4.39 -50.42L-4.39 -50.42L0.00 -50.42L0.00 0.00": "1",
"L0.00 5.35L-29.82 5.35Q-27.67 -8.47 -15.44 -18.60L-15.44 -18.60Q-10.55 -22.57 -8.83 -25.14L-8.83 -25.14Q-6.58 -28.33 -6.58 -32.69L-6.58 -32.69Q-6.58 -36.24 -8.16 -38.46L-8.16 -38.46Q-10.20 -41.55 -14.28 -41.55L-14.28 -41.55Q-22.58 -41.55 -23.35 -29.32L-23.35 -29.32L-29.01 -29.32Q-28.59 -36.63 -25.56 -40.81L-25.56 -40.81Q-21.59 -46.44 -14.14 -46.44L-14.14 -46.44Q-8.93 -46.44 -5.35 -43.42L-5.35 -43.42Q-0.81 -39.51 -0.81 -32.76L-0.81 -32.76Q-0.81 -23.34 -11.47 -15.26L-11.47 -15.26Q-20.57 -8.33 -22.40 0.00L-22.40 0.00L0.00 0.00": "2",
"L0.00 -4.60L3.58 -4.60Q8.19 -4.60 9.91 -5.91L9.91 -5.91Q13.14 -8.40 13.14 -13.39L13.14 -13.39Q13.14 -22.25 5.09 -22.25L5.09 -22.25Q-1.59 -22.25 -3.10 -14.69L-3.10 -14.69L-8.79 -14.69Q-8.02 -19.44 -5.49 -22.53L-5.49 -22.53Q-1.62 -27.14 5.09 -27.14L5.09 -27.14Q10.72 -27.14 14.37 -23.91L14.37 -23.91Q18.70 -20.11 18.70 -13.60L18.70 -13.60Q18.70 -4.85 10.86 -2.14L10.86 -2.14Q20.32 1.51 20.32 11.18L20.32 11.18Q20.32 17.37 16.80 21.34L16.80 21.34Q12.58 26.16 5.20 26.16L5.20 26.16Q-1.73 26.16 -5.84 21.41L-5.84 21.41Q-8.86 17.93 -9.50 11.81L-9.50 11.81L-3.59 11.81Q-2.85 21.20 5.20 21.20L5.20 21.20Q8.93 21.20 11.46 19.09L11.46 19.09Q14.62 16.38 14.62 11.18L14.62 11.18Q14.62 0.00 3.58 0.00L3.58 0.00L0.00 0.00": "3",
"L20.32 -32.91L26.44 -32.91L26.44 0.14L32.42 0.14L32.42 5.02L26.44 5.02L26.44 17.51L21.10 17.51L21.10 5.02L0.00 5.02L0.00 0.00ZM21.10 0.14L21.10 -25.07L5.42 0.14L21.10 0.14": "4",
"L1.23 -28.09L25.14 -28.09L25.14 -23.06L6.26 -23.06L5.49 -6.50Q9.04 -10.58 14.42 -10.58L14.42 -10.58Q20.18 -10.58 23.98 -5.69L23.98 -5.69Q27.60 -0.98 27.60 6.05L27.60 6.05Q27.60 12.06 25.21 16.49L25.21 16.49Q21.20 23.77 12.76 23.77L12.76 23.77Q0.92 23.77 -1.44 10.51L-1.44 10.51L4.33 10.51Q5.52 18.74 12.73 18.74L12.73 18.74Q17.37 18.74 19.94 14.77L19.94 14.77Q22.12 11.43 22.12 6.12L22.12 6.12Q22.12 1.41 20.29 -1.65L20.29 -1.65Q18.04 -5.76 13.47 -5.76L13.47 -5.76Q7.88 -5.76 4.54 0.95L4.54 0.95L0.00 0.00": "5",
"L-5.91 0.00Q-7.00 -7.63 -12.76 -7.63L-12.76 -7.63Q-17.76 -7.63 -20.46 -1.59L-20.46 -1.59Q-22.99 4.07 -23.10 13.74L-23.10 13.74Q-18.99 7.77 -12.62 7.77L-12.62 7.77Q-7.35 7.77 -3.69 11.67L-3.69 11.67Q0.63 16.20 0.63 23.62L0.63 23.62Q0.63 29.81 -2.32 34.41L-2.32 34.41Q-6.33 40.60 -13.61 40.60L-13.61 40.60Q-20.22 40.60 -24.19 34.55L-24.19 34.55Q-28.44 27.91 -28.44 16.13L-28.44 16.13Q-28.44 3.62 -24.72 -4.08L-24.72 -4.08Q-20.46 -12.66 -12.83 -12.66L-12.83 -12.66Q-2.39 -12.66 0.00 0.00L0.00 0.00ZM-13.54 12.44L-13.54 12.44Q-17.72 12.44 -20.25 16.27L-20.25 16.27Q-22.19 19.30 -22.19 23.83L-22.19 23.83Q-22.19 27.91 -20.82 30.76L-20.82 30.76Q-18.42 35.64 -13.47 35.64L-13.47 35.64Q-9.49 35.64 -7.07 32.06L-7.07 32.06Q-4.92 28.89 -4.92 23.76L-4.92 23.76Q-4.92 19.09 -6.79 16.13L-6.79 16.13Q-9.07 12.44 -13.54 12.44": "6",
"L0.00 -5.49L28.79 -5.49L28.79 -1.38Q18.66 23.69 13.60 44.93L13.60 44.93L7.06 44.93Q12.55 25.52 22.60 0.00L22.60 0.00L0.00 0.00": "7",
"L0.00 0.00Q-7.27 -3.55 -7.27 -11.36L-7.27 -11.36Q-7.27 -15.12 -5.48 -18.21L-5.48 -18.21Q-1.68 -24.68 6.19 -24.68L6.19 -24.68Q10.13 -24.68 13.54 -22.61L13.54 -22.61Q19.65 -18.84 19.65 -11.36L19.65 -11.36Q19.65 -3.55 12.38 0.00L12.38 0.00Q21.69 3.59 21.69 13.50L21.69 13.50Q21.69 19.16 18.53 23.20L18.53 23.20Q14.31 28.62 6.19 28.62L6.19 28.62Q-0.70 28.62 -4.88 24.64L-4.88 24.64Q-9.28 20.46 -9.28 13.50L-9.28 13.50Q-9.28 3.59 0.00 0.00ZM6.19 -20.07L6.19 -20.07Q2.57 -20.07 0.28 -17.47L0.28 -17.47Q-1.79 -15.05 -1.79 -11.43L-1.79 -11.43Q-1.79 -9.04 -0.91 -7.10L-0.91 -7.10Q1.23 -2.43 6.26 -2.43L6.26 -2.43Q9.14 -2.43 11.15 -4.22L11.15 -4.22Q14.17 -6.82 14.17 -11.43L14.17 -11.43Q14.17 -15.93 11.15 -18.42L11.15 -18.42Q9.07 -20.07 6.19 -20.07ZM6.12 2.74L6.12 2.74Q1.44 2.74 -1.33 6.19L-1.33 6.19Q-3.65 9.18 -3.65 13.50L-3.65 13.50Q-3.65 17.65 -1.40 20.43L-1.40 20.43Q1.37 23.87 6.19 23.87L6.19 23.87Q11.04 23.87 13.85 20.43L13.85 20.43Q16.07 17.65 16.07 13.50L16.07 13.50Q16.07 8.09 12.76 5.20L12.76 5.20Q10.09 2.74 6.12 2.74": "8",
"L5.91 0.00Q6.79 7.84 13.33 7.84L13.33 7.84Q23.03 7.84 22.93 -12.79L22.93 -12.79Q18.88 -6.85 12.77 -6.85L12.77 -6.85Q5.35 -6.85 1.66 -13.78L1.66 -13.78Q-0.42 -17.82 -0.42 -23.13L-0.42 -23.13Q-0.42 -29.88 3.24 -34.84L3.24 -34.84Q7.18 -40.18 13.33 -40.18L13.33 -40.18Q28.16 -40.18 28.16 -15.11L28.16 -15.11Q28.16 13.12 13.40 13.12L13.40 13.12Q6.65 13.12 2.75 7.28L2.75 7.28Q0.74 4.26 0.00 0.00L0.00 0.00ZM13.57 -35.22L13.57 -35.22Q5.07 -35.22 5.07 -23.27L5.07 -23.27Q5.07 -18.84 6.58 -15.92L6.58 -15.92Q8.83 -11.60 13.57 -11.60L13.57 -11.60Q16.60 -11.60 18.95 -14.27L18.95 -14.27Q21.98 -17.72 21.98 -23.27L21.98 -23.27Q21.98 -28.82 19.59 -32.06L19.59 -32.06Q17.30 -35.22 13.57 -35.22": "9",
"L-5.77 0.00Q-4.36 -11.39 7.28 -11.39L7.28 -11.39Q18.98 -11.39 18.98 1.16L18.98 1.16L18.98 18.35Q18.98 20.39 20.85 20.39L20.85 20.39Q21.48 20.39 22.57 20.15L22.57 20.15L22.57 25.21Q21.13 25.56 19.12 25.56L19.12 25.56Q14.38 25.56 13.74 20.25L13.74 20.25Q8.86 25.56 3.02 25.56L3.02 25.56Q-0.81 25.56 -3.27 23.56L-3.27 23.56Q-6.51 20.96 -6.51 15.86L-6.51 15.86Q-6.51 4.01 13.81 2.60L13.81 2.60L13.81 1.16Q13.81 -6.57 7.28 -6.57L7.28 -6.57Q0.53 -6.57 0.00 0.00L0.00 0.00ZM13.81 11.89L13.81 7.14Q-1.23 7.88 -1.23 15.58L-1.23 15.58Q-1.23 20.74 3.87 20.74L3.87 20.74Q7.35 20.74 10.65 18.07L10.65 18.07Q13.81 15.58 13.81 11.89L13.81 11.89": "a",
"L0.00 -50.42L5.35 -50.42L5.35 -30.34Q9.74 -35.58 14.84 -35.58L14.84 -35.58Q20.15 -35.58 23.49 -30.98L23.49 -30.98Q27.00 -26.06 27.00 -17.44L27.00 -17.44Q27.00 -11.40 25.14 -6.79L25.14 -6.79Q21.80 1.44 14.70 1.44L14.70 1.44Q8.83 1.44 5.28 -4.47L5.28 -4.47L3.91 0.00L0.00 0.00ZM13.54 -30.49L13.54 -30.49Q9.43 -30.49 7.07 -26.30L7.07 -26.30Q5.14 -22.86 5.14 -17.44L5.14 -17.44Q5.14 -11.57 7.21 -7.84L7.21 -7.84Q9.57 -3.66 13.61 -3.66L13.61 -3.66Q17.16 -3.66 19.23 -7.28L19.23 -7.28Q21.38 -10.94 21.38 -17.44L21.38 -17.44Q21.38 -23.81 18.92 -27.32L18.92 -27.32Q16.88 -30.49 13.54 -30.49": "b",
"L5.84 0.00Q3.02 12.91 -7.77 12.91L-7.77 12.91Q-14.27 12.91 -18.07 7.49L-18.07 7.49Q-21.52 2.54 -21.52 -5.62L-21.52 -5.62Q-21.52 -13.39 -18.28 -18.35L-18.28 -18.35Q-14.48 -24.11 -7.84 -24.11L-7.84 -24.11Q2.46 -24.11 5.27 -12.44L5.27 -12.44L-0.49 -12.44Q-2.00 -19.09 -7.77 -19.09L-7.77 -19.09Q-11.43 -19.09 -13.57 -15.71L-13.57 -15.71Q-15.89 -12.09 -15.89 -5.62L-15.89 -5.62Q-15.89 -0.28 -14.31 3.13L-14.31 3.13Q-12.16 7.88 -7.77 7.88L-7.77 7.88Q-1.37 7.88 0.00 0.00L0.00 0.00": "c",
"L0.00 -20.08L5.35 -20.08L5.35 30.34L1.44 30.34L0.07 25.87Q-3.58 31.78 -9.49 31.78L-9.49 31.78Q-14.94 31.78 -18.28 26.50L-18.28 26.50Q-21.65 21.37 -21.65 12.83L-21.65 12.83Q-21.65 5.83 -19.12 1.02L-19.12 1.02Q-15.78 -5.24 -9.56 -5.24L-9.56 -5.24Q-4.39 -5.24 0.00 0.00L0.00 0.00ZM-8.26 -0.15L-8.26 -0.15Q-11.99 -0.15 -14.17 3.90L-14.17 3.90Q-16.03 7.55 -16.03 12.90L-16.03 12.90Q-16.03 18.70 -14.31 22.28L-14.31 22.28Q-12.27 26.68 -8.26 26.68L-8.26 26.68Q-4.64 26.68 -2.25 23.06L-2.25 23.06Q0.21 19.44 0.21 12.90L0.21 12.90Q0.21 7.59 -1.65 4.18L-1.65 4.18Q-3.93 -0.15 -8.26 -0.15": "d",
"L5.63 0.00Q2.50 12.02 -7.98 12.02L-7.98 12.02Q-14.48 12.02 -18.28 6.61L-18.28 6.61Q-21.73 1.65 -21.73 -6.47L-21.73 -6.47Q-21.73 -14.24 -18.49 -19.20L-18.49 -19.20Q-14.69 -24.96 -8.05 -24.96L-8.05 -24.96Q4.92 -24.96 5.77 -5.38L5.77 -5.38L-16.31 -5.38Q-15.89 7.21 -7.91 7.21L-7.91 7.21Q-1.58 7.21 0.00 0.00L0.00 0.00ZM-16.10 -9.99L0.00 -9.99Q-1.16 -20.15 -8.05 -20.15L-8.05 -20.15Q-14.69 -20.15 -16.10 -9.99L-16.10 -9.99": "e",
"L8.71 0.00L8.71 -8.93Q8.71 -16.21 16.13 -16.21L16.13 -16.21L23.90 -16.21L23.90 -11.18L17.15 -11.18Q14.20 -11.18 14.20 -8.51L14.20 -8.51L14.20 0.00L23.90 0.00L23.90 5.03L14.20 5.03L14.20 34.21L8.71 34.21L8.71 5.03L0.00 5.03L0.00 0.00": "f",
"L3.73 0.00L3.73 30.23Q3.73 44.54 -9.42 44.54L-9.42 44.54Q-20.67 44.54 -22.61 33.47L-22.61 33.47L-16.98 33.47Q-16.03 39.72 -9.28 39.72L-9.28 39.72Q-1.44 39.72 -1.44 30.65L-1.44 30.65L-1.44 24.82Q-5.20 29.21 -10.51 29.21L-10.51 29.21Q-16.24 29.21 -20.04 24.68L-20.04 24.68Q-23.48 20.46 -23.48 14.17L-23.48 14.17Q-23.48 9.60 -21.69 6.12L-21.69 6.12Q-17.89 -1.37 -10.23 -1.37L-10.23 -1.37Q-4.89 -1.37 -1.23 2.95L-1.23 2.95L0.00 0.00ZM-9.74 3.58L-9.74 3.58Q-13.71 3.58 -16.07 7.10L-16.07 7.10Q-18.00 9.91 -18.00 14.10L-18.00 14.10Q-18.00 18.46 -15.86 21.37L-15.86 21.37Q-13.53 24.54 -9.67 24.54L-9.67 24.54Q-6.47 24.54 -4.25 22.08L-4.25 22.08Q-1.30 18.91 -1.30 14.17L-1.30 14.17Q-1.30 9.46 -3.83 6.40L-3.83 6.40Q-6.29 3.58 -9.74 3.58": "g",
"L0.00 -50.42L5.35 -50.42L5.35 -30.34Q10.59 -35.58 15.75 -35.58L15.75 -35.58Q21.62 -35.58 24.33 -30.41L24.33 -30.41Q25.84 -27.50 25.84 -23.35L25.84 -23.35L25.84 0.00L20.50 0.00L20.50 -21.77Q20.50 -30.49 14.91 -30.49L14.91 -30.49Q11.15 -30.49 8.30 -27.74L8.30 -27.74Q5.35 -24.79 5.35 -20.99L5.35 -20.99L5.35 0.00L0.00 0.00": "h",
"L0.00 -6.47L6.32 -6.47L6.32 0.00L0.00 0.00ZM0.35 43.95L0.35 9.74L5.97 9.74L5.97 43.95L0.35 43.95": "i",
"L0.00 -6.47L6.33 -6.47L6.33 0.00L0.00 0.00ZM0.32 46.51L0.32 9.74L5.95 9.74L5.95 46.76Q5.95 54.32 -1.40 54.32L-1.40 54.32Q-4.29 54.32 -9.66 53.72L-9.66 53.72L-9.66 48.41Q-6.46 49.15 -2.56 49.15L-2.56 49.15Q0.32 49.15 0.32 46.51L0.32 46.51": "j",
"L0.00 -50.42L5.34 -50.42L5.34 -19.52L17.93 -34.21L24.64 -34.21L13.78 -22.05L27.45 0.00L20.74 0.00L10.44 -18.25L5.34 -12.77L5.34 0.00L0.00 0.00": "k",
"L0.00 42.54Q0.00 45.63 2.96 45.63L2.96 45.63Q5.38 45.63 8.26 45.07L8.26 45.07L8.26 50.45Q4.01 51.05 2.01 51.05L2.01 51.05Q-5.62 51.05 -5.62 43.56L-5.62 43.56L-5.62 0.00L0.00 0.00": "l",
"L3.80 0.00L4.61 2.67Q7.67 -1.37 11.01 -1.37L11.01 -1.37Q14.35 -1.37 16.18 2.67L16.18 2.67Q19.38 -1.37 23.21 -1.37L23.21 -1.37Q29.40 -1.37 29.40 7.28L29.40 7.28L29.40 34.21L24.23 34.21L24.23 8.26Q24.23 3.23 21.70 3.23L21.70 3.23Q19.41 3.23 18.00 5.76L18.00 5.76Q17.20 7.35 17.20 9.21L17.20 9.21L17.20 34.21L12.17 34.21L12.17 8.19Q12.17 3.23 9.57 3.23L9.57 3.23Q5.17 3.23 5.17 9.14L5.17 9.14L5.17 34.21L0.00 34.21L0.00 0.00": "m",
"L4.26 0.00L5.07 4.39Q10.48 -1.37 15.75 -1.37L15.75 -1.37Q21.62 -1.37 24.33 3.80L24.33 3.80Q25.84 6.71 25.84 10.86L25.84 10.86L25.84 34.21L20.50 34.21L20.50 12.44Q20.50 3.72 14.91 3.72L14.91 3.72Q11.11 3.72 8.30 6.47L8.30 6.47Q5.35 9.42 5.35 13.25L5.35 13.25L5.35 34.21L0.00 34.21L0.00 0.00": "n",
"L0.00 0.00Q6.61 0.00 10.37 5.83L10.37 5.83Q13.61 10.68 13.61 18.49L13.61 18.49Q13.61 24.36 11.67 28.79L11.67 28.79Q8.09 37.02 -0.14 37.02L-0.14 37.02Q-6.50 37.02 -10.30 31.60L-10.30 31.60Q-13.75 26.65 -13.75 18.49L-13.75 18.49Q-13.75 9.70 -9.77 4.67L-9.77 4.67Q-5.98 0.00 0.00 0.00ZM-0.14 5.02L-0.14 5.02Q-4.01 5.02 -6.19 9.07L-6.19 9.07Q-8.12 12.62 -8.12 18.49L-8.12 18.49Q-8.12 23.90 -6.54 27.31L-6.54 27.31Q-4.36 31.99 -0.07 31.99L-0.07 31.99Q3.87 31.99 6.05 27.95L6.05 27.95Q7.98 24.40 7.98 18.56L7.98 18.56Q7.98 12.48 5.98 9.00L5.98 9.00Q3.83 5.02 -0.14 5.02": "o",
"L3.98 0.00L4.86 4.53Q9.67 -1.37 14.84 -1.37L14.84 -1.37Q20.11 -1.37 23.49 3.30L23.49 3.30Q27.07 8.33 27.07 16.31L27.07 16.31Q27.07 23.76 24.19 28.76L24.19 28.76Q20.78 34.66 14.77 34.66L14.77 34.66Q9.57 34.66 5.35 29.92L5.35 29.92L5.35 44.54L0.00 44.54L0.00 0.00ZM13.61 3.72L13.61 3.72Q10.09 3.72 7.63 7.24L7.63 7.24Q5.14 10.86 5.14 16.38L5.14 16.38Q5.14 21.41 6.86 24.75L6.86 24.75Q9.21 29.49 13.68 29.49L13.68 29.49Q17.23 29.49 19.30 26.12L19.30 26.12Q21.38 22.46 21.38 16.38L21.38 16.38Q21.38 10.83 19.45 7.45L19.45 7.45Q17.30 3.72 13.61 3.72": "p",
"L-5.35 0.00L-5.35 -14.62Q-9.57 -9.88 -14.77 -9.88L-14.77 -9.88Q-20.15 -9.88 -23.49 -14.69L-23.49 -14.69Q-27.07 -19.83 -27.07 -28.23L-27.07 -28.23Q-27.07 -34.94 -24.47 -39.58L-24.47 -39.58Q-21.06 -45.91 -14.91 -45.91L-14.91 -45.91Q-9.78 -45.91 -4.86 -40.01L-4.86 -40.01L-3.98 -44.54L0.00 -44.54L0.00 0.00ZM-13.68 -40.82L-13.68 -40.82Q-17.37 -40.82 -19.45 -36.98L-19.45 -36.98Q-21.38 -33.64 -21.38 -28.09L-21.38 -28.09Q-21.38 -15.05 -13.61 -15.05L-13.61 -15.05Q-9.57 -15.05 -7.07 -19.37L-7.07 -19.37Q-5.14 -22.82 -5.14 -28.16L-5.14 -28.16Q-5.14 -34.56 -8.37 -38.21L-8.37 -38.21Q-10.62 -40.82 -13.68 -40.82": "q",
"L5.49 0.00L5.49 7.21Q11.71 0.63 18.81 -1.37L18.81 -1.37L18.81 4.89Q10.65 6.85 5.49 13.74L5.49 13.74L5.49 34.21L0.00 34.21L0.00 0.00": "r",
"L5.70 0.00Q6.65 7.21 14.10 7.21L14.10 7.21Q21.59 7.21 21.59 1.93L21.59 1.93Q21.59 -0.60 19.87 -2.01L19.87 -2.01Q18.04 -3.52 13.33 -5.17L13.33 -5.17L12.31 -5.56Q7.11 -7.35 4.75 -9.14L4.75 -9.14Q1.38 -11.78 1.38 -15.51L1.38 -15.51Q1.38 -19.97 5.28 -22.68L5.28 -22.68Q8.65 -25.00 13.47 -25.00L13.47 -25.00Q24.33 -25.00 26.06 -15.12L26.06 -15.12L20.47 -15.12Q19.59 -20.39 13.40 -20.39L13.40 -20.39Q6.79 -20.39 6.79 -15.72L6.79 -15.72Q6.79 -12.66 15.65 -9.53L15.65 -9.53Q20.64 -7.77 22.82 -6.19L22.82 -6.19Q27.07 -3.17 27.07 1.79L27.07 1.79Q27.07 6.61 23.28 9.42L23.28 9.42Q19.69 12.02 13.96 12.02L13.96 12.02Q1.41 12.02 0.00 0.00L0.00 0.00": "s",
"L0.00 -9.28L5.49 -9.28L5.49 0.00L13.96 0.00L13.96 5.17L5.49 5.17L5.49 26.96Q5.49 29.42 8.23 29.42L8.23 29.42Q11.57 29.42 14.45 28.86L14.45 28.86L14.45 34.24Q10.20 34.84 7.14 34.84L7.14 34.84Q0.00 34.84 0.00 27.70L0.00 27.70L0.00 5.17L-6.78 5.17L-6.78 0.00L0.00 0.00": "t",
"L0.00 -23.76L5.35 -23.76L5.35 -0.56Q5.35 6.86 11.22 6.86L11.22 6.86Q15.02 6.86 17.90 4.05L17.90 4.05Q20.50 1.55 20.50 -2.53L20.50 -2.53L20.50 -23.76L25.84 -23.76L25.84 10.45L21.87 10.45L20.92 6.40Q16.21 11.89 10.02 11.89L10.02 11.89Q4.64 11.89 1.94 7.77L1.94 7.77Q0.00 4.75 0.00 0.00L0.00 0.00": "u",
"L-11.39 -34.21L-5.35 -34.21L2.95 -6.58L11.21 -34.21L17.26 -34.21L5.90 0.00L0.00 0.00": "v",
"L-5.10 -34.21L-0.07 -34.21L2.96 -8.02L8.02 -34.21L13.47 -34.21L18.53 -8.02L21.55 -34.21L26.58 -34.21L21.48 0.00L15.93 0.00L10.76 -26.65L5.56 0.00L0.00 0.00": "w",
"L-9.67 -15.33L-3.10 -15.33L3.02 -4.12L9.14 -15.33L15.68 -15.33L6.04 0.00L17.93 18.88L10.93 18.88L3.02 4.67L-4.89 18.88L-11.89 18.88L0.00 0.00": "x",
"L-12.10 -31.18L-5.91 -31.18L2.67 -6.85L10.23 -31.18L16.49 -31.18L2.35 8.33Q1.19 11.78 -1.65 12.87L-1.65 12.87Q-2.99 13.40 -10.16 13.40L-10.16 13.40L-10.16 8.19L-7.07 8.19Q-5.98 8.19 -5.49 8.19L-5.49 8.19Q-3.06 8.19 -2.32 6.26L-2.32 6.26L0.00 0.00": "y",
"L0.00 -5.03L23.45 -5.03L23.45 -0.57L4.96 24.15L24.47 24.15L24.47 29.18L-1.23 29.18L-1.23 24.08L16.63 0.00L0.00 0.00": "z",
}

def decode_letter(encletter: str) -> str:
    return translation_dict[encletter[10:-1]]  # if this going to fail you're doomed anyway


def solvesvg(svg: str) -> str:  # i have absolute fucking no idea how it works.
    # moving around functions for 4 hours straight doesn't help with understanding this in the slightest
    # if you're mad enough to refactor this piece of shit then i wanna wish you a fucking good luck, you will need it
    answer = ""
    outstr = ""
    float_start = 0
    ammount_of_floats = 0
    ammount_of_floats_extracted = 0
    is_m = False
    reading_letter=True
    maxx = 0
    last_hit_z = False
    basex, basey = 0, 0

    for i, char in enumerate(svg):
        if not reading_letter:
            if not char.isdigit() and char != ".":
                ammount_of_floats -= 1

                tmpnum = float(svg[float_start:i])
                if last_hit_z and maxx < tmpnum and is_m:
                    outstr += decode_letter(answer)
                    answer = ""
                    last_hit_z = False
                if is_m:
                    if last_hit_z and maxx > basex:
                        if ammount_of_floats_extracted % 2 == 0:
                            answer += "M"
                            oldx = basex
                            basex = tmpnum  # it's x
                            answer += "{:.2f} ".format(tmpnum - oldx)
                            basex = oldx
                        else:
                            oldy = basey
                            basey = tmpnum  # it's y
                            answer += "{:.2f}".format(tmpnum - oldy)
                            basey = oldy
                    else:
                        if ammount_of_floats_extracted % 2 == 0:
                            answer += "M"
                            basex = tmpnum  # it's x
                            answer += "{:.2f} ".format(tmpnum - basex)
                        else:
                            basey = tmpnum  # it's y
                            answer += "{:.2f}".format(tmpnum - basey)
                else:
                    if ammount_of_floats_extracted % 2 == 0:
                        answer += "{:.2f} ".format(tmpnum - basex)
                    else:
                        answer += "{:.2f}".format(tmpnum - basey)
                if ammount_of_floats == 2:
                    answer += " " # hacky
                if maxx < tmpnum and ammount_of_floats_extracted % 2 == 0:
                    maxx = tmpnum
                float_start = i+1

                ammount_of_floats_extracted += 1
                if ammount_of_floats == 0:
                    reading_letter = True
        if reading_letter:
            is_m = False
            reading_letter = False
            float_start = i + 1
            if char == "M":
                ammount_of_floats = 2
                is_m = True
            elif char == "L":
                answer += "L"
                ammount_of_floats = 2
            elif char == "Q":
                answer += "Q"
                ammount_of_floats = 4
            elif char == "Z":
                answer += "Z"
                last_hit_z = True
                reading_letter = True
            else:
                print("bad!")

    outstr += decode_letter(answer)

    return outstr


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
    # print(solvesvg("M32.63 54.35L32.63 59.70L2.81 59.70Q4.96 45.88 17.19 35.75L17.19 35.75Q22.08 31.78 23.80 29.21L23.80 29.21Q26.05 26.02 26.05 21.66L26.05 21.66Q26.05 18.11 24.47 15.89L24.47 15.89Q22.43 12.80 18.35 12.80L18.35 12.80Q10.05 12.80 9.28 25.03L9.28 25.03L3.62 25.03Q4.04 17.72 7.07 13.54L7.07 13.54Q11.04 7.91 18.49 7.91L18.49 7.91Q23.70 7.91 27.28 10.93L27.28 10.93Q31.82 14.84 31.82 21.59L31.82 21.59Q31.82 31.01 21.16 39.09L21.16 39.09Q12.06 46.02 10.23 54.35L10.23 54.35L32.63 54.35ZM51.05 59.70L39.66 25.49L45.70 25.49L54 53.12L62.26 25.49L68.31 25.49L56.95 59.70L51.05 59.70ZM93.97 59.70L88.07 59.70L88.07 16.63Q85.36 18.46 80.51 20.50L80.51 20.50L80.51 14.70Q86.13 12.62 89.58 9.28L89.58 9.28L93.97 9.28L93.97 59.70ZM126 7.84L126 7.84Q139.99 7.84 139.99 34.49L139.99 34.49Q139.99 61.14 126 61.14L126 61.14Q112.04 61.14 112.04 34.49L112.04 34.49Q112.04 7.84 126 7.84ZM118.97 47.00L118.97 47.00L131.84 17.65Q129.80 12.80 125.93 12.80L125.93 12.80Q117.95 12.80 117.95 34.49L117.95 34.49Q117.95 41.87 118.97 47.00ZM133.07 22.01L120.16 51.26Q122.13 56.18 126 56.18L126 56.18Q134.09 56.18 134.09 34.42L134.09 34.42Q134.09 27.21 133.07 22.01L133.07 22.01ZM176.03 20.50L170.12 20.50Q169.03 12.87 163.27 12.87L163.27 12.87Q158.27 12.87 155.57 18.91L155.57 18.91Q153.04 24.57 152.93 34.24L152.93 34.24Q157.04 28.27 163.41 28.27L163.41 28.27Q168.68 28.27 172.34 32.17L172.34 32.17Q176.66 36.70 176.66 44.12L176.66 44.12Q176.66 50.31 173.71 54.91L173.71 54.91Q169.70 61.10 162.42 61.10L162.42 61.10Q155.81 61.10 151.84 55.05L151.84 55.05Q147.59 48.41 147.59 36.63L147.59 36.63Q147.59 24.12 151.31 16.42L151.31 16.42Q155.57 7.84 163.20 7.84L163.20 7.84Q173.64 7.84 176.03 20.50L176.03 20.50ZM162.49 32.94L162.49 32.94Q158.31 32.94 155.78 36.77L155.78 36.77Q153.84 39.80 153.84 44.33L153.84 44.33Q153.84 48.41 155.21 51.26L155.21 51.26Q157.61 56.14 162.56 56.14L162.56 56.14Q166.54 56.14 168.96 52.56L168.96 52.56Q171.11 49.39 171.11 44.26L171.11 44.26Q171.11 39.59 169.24 36.63L169.24 36.63Q166.96 32.94 162.49 32.94Z"))


