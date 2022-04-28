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
        self.sendanswer = False
        self.question = None
        self.placeholder = None
        self.answer = None

    def onBeforeRequest(self, id) -> bool:
        self.id = id
        return True  # TODO: When try_questions is false, query the server for answers here

    def solve(self, captchaBlockSoup) -> Union[dict, None]:
        time.sleep(settings.solve_time)
        self.question = captchaBlockSoup.find("div", attrs={"class": "ddText"}).text

        # TODO: add exact threadid search
        params = {
            "id": self.id
        }
        if settings.try_questions:
            params["q"] = self.question
            placeholdertext = captchaBlockSoup.find("input", attrs={"id": "CaptchaQuestionAnswer"})["placeholder"]
            if placeholdertext:
                self.placeholder = pattern_hint_letter.search(placeholdertext).group(1)
                params["l"] = self.placeholder

        response = self.puser.makerequest("GET", "https://" + settings.answers_server + "/query.php", params=params,
                                          timeout=12.05, retries=3, checkforjs=False)

        if response is None:
            return None

        resp = response.json()

        returnval = None
        if resp["status"] == 0:
            self.answer = resp["answer"]

            returnval = {
                'captcha_question_answer': self.answer,
                'captcha_type': "AnswerCaptcha",
            }
        elif resp["status"] == -1:
            self.puser.logger.warning("%d doesn't have an answer. blacklisting for 5 minutes", self.id)
            settings.ExpireBlacklist[self.id] = time.time() + 300 # TODO: make configurable timeout
        elif resp["status"] == 1: # TODO: make this check configurable
            if settings.try_questions:
                self.answer = resp["answer"]
                returnval = {
                    'captcha_question_answer': self.answer,
                    'captcha_type': "AnswerCaptcha",
                }
                self.sendanswer = True
            else:
                self.puser.logger.warning("%d %d answer isn't exact. blacklisting for 5 minutes", resp["threadid"], resp["id"])
                settings.ExpireBlacklist[self.id] = time.time() + 300
        else:
            raise RuntimeError("Answers server: unknown response status. You should probably update")
        self.puser.logger.verbose("threadid:%s, answer id:%s, status:%d, question:%s, placeholder:%s, answer:%s",
                                  resp.get("threadid", self.id),
                                  resp.get("id", None),
                                  resp["status"],
                                  self.question,
                                  self.placeholder,
                                  self.answer)
        return returnval

    def onFailure(self, response):
        self.puser.logger.error("%d didn't participate (wrong answer?): %s", self.id, str(response))
        settings.ExpireBlacklist[self.id] = time.time() + 300000

    def onSuccess(self, response):
        self.puser.logger.debug("%s", str(response))
        if self.sendanswer:
            if self.question is None or self.answer is None or self.id == -1:
                raise RuntimeError("onSuccess illegal state: question, answer or id is null")
            self.puser.logger.debug("Submitting the answer to the answers server")
            params = {
                "id": self.id,
                "q": self.question,
                "a": self.answer,
            }
            if self.placeholder:
                params["l"] = self.placeholder
            response = self.puser.makerequest("POST", "https://" + settings.answers_server + "/submit.php", params=params,
                                              timeout=12.05, retries=3, checkforjs=False)

            if response is None:
                self.puser.logger.warning("There was an issue submitting the answer")
                return

            status = response.json()["status"]
            if status == 0:
                self.puser.logger.debug("Successfully submitted the answer")
            else:
                raise RuntimeError("Answers server: unknown response status. You should probably update")
