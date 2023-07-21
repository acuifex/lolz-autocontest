import re
import time
from urllib.parse import quote

from bs4 import BeautifulSoup

from settings import settings


class SolverTurnsile:
    def __init__(self, puser):
        self.puser = puser
        self.id = -1
        self.turnsile_response = None
        self.request_time = None

    def on_before_request(self, id) -> bool:
        self.id = id
        return True

    def solve(self, contest_soup: BeautifulSoup) -> bool:
        time.sleep(settings.solve_time)

        contest_captcha = contest_soup.find("div", class_="ContestCaptcha")
        if contest_captcha is None:
            self.puser.logger.warning("Couldn't get ContestCaptcha. Lag or contest is over?")
            return False

        message_content = contest_soup.find("div", {"class": "messageContent"})

        # TODO: this looks ugly.
        contest_thread_block = message_content.find("div", {"class": "contestThreadBlock"})
        if contest_thread_block is not None:
            for contest_info in contest_thread_block.find_all("div", {"class": "marginBlock"}, recursive=False):
                # https://youtu.be/FBdFhgWYEjM
                if re.match("\s*Приз:\s+Слив фотографий", contest_info.text):
                    settings._expire_blacklist[self.id] = time.time() + 30000000000
                    self.puser.logger.notice("saved your ass from a useless contest")
                    return False

        self.request_time = contest_captcha.find("input", {"name": "request_time"}, recursive=False)
        if self.request_time is None:
            self.puser.logger.warning("request_time is missing.")
            return False

        self.turnsile_response = self.request_turnsile_solve()
        if self.turnsile_response is None:
            return False
        return True

    def request_turnsile_solve(self):
        params = {
            'clientKey': settings.anti_captcha_key,
            'task': {
                'type': "TurnstileTaskProxyless",
                'websiteKey': settings.site_key,
                'websiteURL': settings.lolz_url + "threads/" + str(self.id) + "/",
            }
        }

        submitresp = self.puser.makerequest("POST", "https://api.capmonster.cloud/createTask", json=params)

        if submitresp is None:
            self.puser.logger.warning("couldn't send turnsile solve request")
            return None

        submit = submitresp.json()
        self.puser.logger.debug(submit)
        if submit["errorId"] != 0:
            self.puser.logger.warning("turnsile captcha submit was unsuccessful")
            return None

        while True:
            time.sleep(5)
            resp = self.puser.makerequest(
                "POST",
                "https://api.capmonster.cloud/getTaskResult",
                json={
                    'clientKey': settings.anti_captcha_key,
                    'taskId': submit["taskId"],
                }
            )
            if resp is None:
                self.puser.logger.warning("turnsile solve fetch failed")
                continue

            answer = resp.json()
            self.puser.logger.debug(answer)
            if answer["status"] == "processing":
                continue
            if answer["errorId"] != 0:
                self.puser.logger.warning("service failed to solve captcha")
                return None
            if answer["status"] == "ready":
                return answer["solution"]["token"]
            else:
                raise RuntimeError("unknown response from captcha solver")

    def participate(self, csrf: str):
        if self.turnsile_response is None or self.request_time is None:
            raise RuntimeError("turnsile_response or request_time is none when participating")

        response = self.puser.makerequest(
            "POST",
            settings.lolz_url + "threads/" + str(self.id) + "/participate",
            params={"cf-turnstile-response": self.turnsile_response},
            data={
                'request_time': str(self.request_time),
                'cf-turnstile-response': self.turnsile_response,
                '_xfRequestUri': quote("/threads/" + str(self.id) + "/"),
                '_xfNoRedirect': 1,
                '_xfToken': csrf,
                '_xfResponseType': "json",
            },
            timeout=12.05,
            retries=3,
            checkforjs=True
        )

        if response is None:
            return None

        return response.json()

    def on_failure(self, response):
        self.puser.logger.error("%d didn't participate (why lol?): %s", self.id, str(response))
        settings._expire_blacklist[self.id] = time.time() + 300000

    def on_success(self, response):
        self.puser.logger.debug("%s", str(response))
