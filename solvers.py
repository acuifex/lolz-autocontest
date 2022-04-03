import re
from typing import Union
import time

import settings

pattern_captcha_sid = re.compile(r"sid\s*:\s*'([0-9a-f]{32})'", re.MULTILINE)
pattern_captcha_dot = re.compile(r'XenForo.ClickCaptcha.dotSize\s*=\s*(\d+);', re.MULTILINE)
pattern_captcha_img = re.compile(r'XenForo.ClickCaptcha.imgData\s*=\s*"([A-Za-z0-9+/=]+)";', re.MULTILINE)
pattern_hint_letter = re.compile(r'Starts with \'(.)\' letter', re.MULTILINE)


class SolverAnswers:
    def __init__(self, puser):
        self.puser = puser
        self.id = -1

    def onBeforeRequest(self, id) -> bool:
        self.id = id
        return True  # TODO: move requests to the answers server here

    def solve(self, captchaBlockSoup) -> Union[dict, None]:
        time.sleep(settings.solve_time)
        question = captchaBlockSoup.find("div", attrs={"class": "ddText"}).text
        placeholder = captchaBlockSoup.find("input", attrs={"id": "CaptchaQuestionAnswer"})["placeholder"]

        # TODO: add exact threadid search
        params = {
            "id": self.id,
            "q": question,
        }

        if placeholder:
            params["l"] = pattern_hint_letter.search(placeholder).group(1)

        response = self.puser.makerequest("GET", "https://" + settings.answers_server + "/query.php", params=params,
                                          timeout=12.05, retries=3, checkforjs=False)

        if response is None:
            return None

        resp = response.json()

        if resp["status"] == 0:
            pass
        elif resp["status"] == -1:
            self.puser.logger.warning("%d doesn't have an answer. blacklisting for 5 minutes", self.id)
            settings.ExpireBlacklist[self.id] = time.time() + 300 # TODO: make configurable timeout
            return None
        elif resp["status"] == 1: # TODO: make this check configurable
            self.puser.logger.warning("%d %d answer isn't exact. blacklisting for 5 minutes", resp["threadid"], resp["id"])
            settings.ExpireBlacklist[self.id] = time.time() + 300
            return None
        else:
            raise RuntimeError("Answers server: unknown response status. You should probably update")

        self.puser.logger.verbose("threadid:%d, answer id:%d, status:%d", resp["threadid"], resp["id"], resp["status"])
        return {
            'captcha_question_answer': resp["answer"],
            'captcha_type': "AnswerCaptcha",
        }

    def onFailure(self, response):
        self.puser.logger.error("%s has wrong answer", self.id)
        settings.ExpireBlacklist[self.id] = time.time() + 300000
