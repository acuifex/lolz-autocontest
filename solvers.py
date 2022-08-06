import copy
import hashlib
import re
import time
from pathlib import Path
from typing import Union

from bs4 import BeautifulSoup

import settings

known_hashes = {
    "6b6b50b876cb7ac612021610fd13cd93b6b734ad801d34f93373dbe3b47f2dc2": "money",
    "bb40b0a905fbb715c324ba30c3ad73867728ef08e237c50d41a99e39b9f57e80": "money (no likes requirement)",
    "6da54c99814385049926e0871f865648a576a7ef9930071af503d307e9910b9b": "money (edited)",
    # "MAKE THIS ONE YOURSELF LATER": "money (edited + no likes requirement)",
    "54bd5174b3f0b3a484fa1acc760f136890372d27e7cb45f36f148e4221c74954": "money (multiple)",
    "2c593b80777dd877a8ffb708b203a84c47aa7cf1a8ea866dfc105205b0e0a990": "money (multiple + edited)",
    "7eddfce84b8e86eff974299f596bd3afdadb5e0b78bb4fb784902accee1c729d": "money (multiple + no likes requirement)",
    "8371d07ce8ad7a2f438e848ebb94fb90e59900337ad5299c926fea3cbcb347dd": "money (multiple + no likes requirement + edited)",
    "864f281c3074cfa190bec51172237c394964038608c2e86ff0d74786e06939d0": "items"  # missing money entry
    # "MAKE THIS ONE YOURSELF LATER": "items (no likes requirement)",
    # "MAKE THIS ONE YOURSELF LATER": "items (edited)",
    # "MAKE THIS ONE YOURSELF LATER": "items (edited + no likes requirement)",
    # "MAKE THIS ONE YOURSELF LATER": "items (multiple)",
    # "MAKE THIS ONE YOURSELF LATER": "items (multiple + edited)",
    # "MAKE THIS ONE YOURSELF LATER": "items (multiple + no likes requirement)",
    # "MAKE THIS ONE YOURSELF LATER": "items (multiple + no likes requirement + edited)",
    # TODO: some contests can have empty public controls. it might be related to contests created "just now"
    #"5e0696894179d53cbdc2ca7c43a4f883617e947449726c4438550c9a00d4f6c6": "items (without likes)"  # rare variation? bug?
}

class SolverFakeButton:
    def __init__(self, puser):
        self.puser = puser
        self.id = -1

    def onBeforeRequest(self, id) -> bool:
        self.id = id
        return True

    # please someone review these two functions bellow for any bypasses
    def hardenContestInfo(self, soupMarginBlock: BeautifulSoup):
        # if re.match("\s*Завершение через \d+ (дня|день) \d+ час(а|ов) \d+ минуты? \d+ секунды?", soupMarginBlock.text):
        # fuck russian
        if re.match("\s*Завершение через(?: \d+ д\w{0,4})?(?: \d+ час\w{0,4})?(?: \d+ минут\w{0,4})?(?: \d+ секунд\w{0,4})?", soupMarginBlock.text):
            # https://stackoverflow.com/a/24542398
            match = soupMarginBlock.find(text=re.compile("^(?!\s*$)(?: \d+ д\w{0,4})?(?: \d+ час\w{0,4})?(?: \d+ минут\w{0,4})?(?: \d+ секунд\w{0,4})?\s*$", flags=re.MULTILINE), recursive=False)
            if match is not None:
                match.string.replace_with(re.sub("^(?!\s*$)(?: \d+ д\w{0,4})?(?: \d+ час\w{0,4})?(?: \d+ минут\w{0,4})?(?: \d+ секунд\w{0,4})?\s*$", " 2 дня 23 часа 59 минут", match.string, flags=re.MULTILINE))
        elif re.match("\s*Приняли участие: \d+ пользовате\w{0,6}", soupMarginBlock.text):
            match = soupMarginBlock.find(text=re.compile("^ \d+ пользовате\w{0,6}\s*$", flags=re.MULTILINE), recursive=False)
            if match is not None:
                match.string.replace_with(re.sub("^ \d+ пользовате\w{0,6}\s*$", " 42 пользователей", match.string, flags=re.MULTILINE))
        elif re.match("\s*Количество призов: \d+", soupMarginBlock.text):
            match = soupMarginBlock.find(text=re.compile("^ \d+\s*$", flags=re.MULTILINE), recursive=False)
            if match is not None:
                match.string.replace_with(re.sub("^ \d+\s*$", " 42", match.string, flags=re.MULTILINE))
        elif re.match("\s*Приз:\s+Деньги\s+\(\d+ ₽(?: x \d+)?\)", soupMarginBlock.text):
            bold = soupMarginBlock.find("span", {"class":"bold"}, recursive=False)
            if bold is not None:
                bold.string = re.sub("^\s+Деньги\s+\(\d+ ₽(?: x \d+)?\)\s+$", "Деньги (420 ₽)", bold.string, flags=re.MULTILINE)

        elif re.match("\s*Необходимо набрать за 7 дней \d+ симп\w{0,8}", soupMarginBlock.text):
            match = soupMarginBlock.find(
                text=re.compile("^Необходимо набрать за 7 дней \d+ симп\w{0,8}$", flags=re.MULTILINE),
                recursive=False)
            if match is not None:
                match.string.replace_with(
                    re.sub("^Необходимо набрать за 7 дней \d+ симп\w{0,8}$",
                           "Необходимо набрать за 7 дней 100 симпатий", match.string, flags=re.MULTILINE))

        elif re.match("\s*Необходимо набрать за все время \d+ симп\w{0,8}", soupMarginBlock.text):
            match = soupMarginBlock.find(text=re.compile("^Необходимо набрать за все время \d+ симп\w{0,8}$", flags=re.MULTILINE),
                                         recursive=False)
            if match is not None:
                match.string.replace_with(
                    re.sub("^Необходимо набрать за все время \d+ симп\w{0,8}$", "Необходимо набрать за все время 1 симпатию", match.string, flags=re.MULTILINE))
        elif re.match("\s*Бот выбирает победителей случайным образом\.", soupMarginBlock.text):
            pass  # Do nothing
        pass

    # this is a dimension without PEP 505
    def hardenMessageContent(self, soupMessageContent: BeautifulSoup):
        article = soupMessageContent.find("article", recursive=False)
        if article is not None:
            usercontent = article.find("blockquote", {"class": "messageText SelectQuoteContainer baseHtml ugc"},
                                       recursive=False)
            if usercontent is not None:
                usercontent.clear()  # nuke all user content
            contestThreadBlock = article.find("div", {"class": "contestThreadBlock"}, recursive=False)
            if contestThreadBlock is not None:
                for captchainfo in contestThreadBlock.find_all("div", {"class": "marginBlock"}, recursive=False):
                    self.hardenContestInfo(captchainfo)
                contestcaptcha = contestThreadBlock.find("div", {"class": "ContestCaptcha mn-15-0-0"}, recursive=False)
                if contestcaptcha is not None:
                    if contestcaptcha.get("data-refresh-url") is not None:
                        contestcaptcha["data-refresh-url"] = re.sub("^threads/\d+/contest/captcha$",
                                                                    "threads/4154883/contest/captcha",
                                                                    contestcaptcha["data-refresh-url"], flags=re.MULTILINE)

                    requestTime = contestcaptcha.find("input", {"type": "hidden", "name": "request_time"},
                                                      recursive=False)
                    if requestTime is not None:
                        if requestTime.get("value") is not None:
                            requestTime["value"] = re.sub("^\d+$", "1000166400", requestTime["value"], flags=re.MULTILINE)

                    xftoken = contestcaptcha.find("input", {"type": "hidden", "name": "_xfToken"}, recursive=False)
                    if xftoken is not None:
                        if xftoken.get("value") is not None:
                            xftoken["value"] = re.sub("^\d+,\d+,[0-9a-f]{40}$",
                                                      "136698,1000166400,26b4d80b759884633282c1e4d8b42e12b3776249",
                                                      xftoken["value"], flags=re.MULTILINE)

                participate = contestThreadBlock.find("a",
                                                      {"class": "LztContest--Participate button mn-15-0-0 primary"},
                                                      recursive=False)
                if participate is not None:
                    if participate.get("href") is not None:
                        participate["href"] = re.sub("^threads/\d+/participate$",
                                                     "threads/4154883/participate",
                                                     participate["href"], flags=re.MULTILINE)

        messageMeta = soupMessageContent.find("div", {"class": "messageMeta ToggleTriggerAnchor"}, recursive=False)
        if messageMeta is not None:
            privateControls = messageMeta.find("div", {"class": "privateControls"}, recursive=False)
            if privateControls is not None:
                permalink = privateControls.find("a",
                                                 {
                                                     "class": "item messageDateInBottom datePermalink hashPermalink OverlayTrigger muted",
                                                     "title": "Постоянная ссылка"}, recursive=False)
                if permalink is not None:
                    if permalink.get("href") is not None:
                        permalink["href"] = re.sub("^threads/\d+/$",
                                                   "threads/4154883/",
                                                   permalink["href"], flags=re.MULTILINE)
                    if permalink.get("data-href") is not None:
                        permalink["data-href"] = re.sub("^posts/\d+/permalink$",
                                                        "posts/32607564/permalink",
                                                        permalink["data-href"], flags=re.MULTILINE)

                    datetime = permalink.find("abbr", {"class": "DateTime"}, recursive=False)
                    if datetime is not None:
                        if datetime.get("data-time") is not None:
                            datetime["data-time"] = re.sub("^\d+$", "1000166400", datetime["data-time"], flags=re.MULTILINE)
                        if datetime.get("data-diff") is not None:
                            datetime["data-diff"] = re.sub("^\d+$", "42", datetime["data-diff"], flags=re.MULTILINE)
                        if datetime.get("data-datestring") is not None:
                            datetime["data-datestring"] = re.sub("^\d+ \w+ \d+$", "11 сен 2001",
                                                                 datetime["data-datestring"], flags=re.MULTILINE)
                        if datetime.get("data-timestring") is not None:
                            datetime["data-timestring"] = re.sub("^\d+:\d+$", "00:00", datetime["data-timestring"], flags=re.MULTILINE)
                        datetime.string = re.sub("^\d+ \w+ \d+ в \d+:\d+$", "11 сен 2001 в 00:00", datetime.string, flags=re.MULTILINE)
                changed = privateControls.find("span", {"class": "item muted hiddenNarrowUnder"}, recursive=False)
                if changed is not None:
                    changedtooltip = changed.find("span",
                                                  {
                                                      "class": "Tooltip",
                                                      "title": re.compile("^Отредактировал .+$", flags=re.MULTILINE)
                                                  }, recursive=False)
                    if changedtooltip is not None:
                        if re.match("^\s*Изменено\s*$", changedtooltip.text, flags=re.MULTILINE):
                            changedtooltip["title"] = "Отредактировал acuifex 1 мин. назад"
            publicControls = messageMeta.find("div", {"class": "publicControls"}, recursive=False)
            if publicControls is not None:
                likesLink = publicControls.find("span",  # was "a" a week ago
                                                {"class": "Tooltip PopupTooltip LikeLink item control like",
                                                 "data-content": ".TooltipContent"}, recursive=False)
                if likesLink is not None:
                    if likesLink.get("href") is not None:  # was removed when a changed to span, i'll leave it here just in case
                        likesLink["href"] = re.sub("^posts/\d+/like$",
                                                   "posts/32607564/like",
                                                   likesLink["href"], flags=re.MULTILINE)
                    if likesLink.get("data-likes-url") is not None:
                        likesLink["data-likes-url"] = re.sub("^posts/\d+/likes-inline$",
                                                             "posts/32607564/likes-inline",
                                                             likesLink["data-likes-url"], flags=re.MULTILINE)
                    if likesLink.get("data-container") is not None:
                        likesLink["data-container"] = re.sub("^#likes-post-\d+$",
                                                             "#likes-post-32607564",
                                                             likesLink["data-container"], flags=re.MULTILINE)
                    likeLabel = likesLink.find("span", {"class": "LikeLabel"}, recursive=False)
                    if likeLabel is not None:
                        likeLabel.string = re.sub("^\d+$", "42", likeLabel.string, flags=re.MULTILINE)
                tooltipContent = publicControls.find("div", {"class": "TooltipContent"}, recursive=False)
                if tooltipContent is not None:
                    if tooltipContent.get("id") is not None:
                        tooltipContent["id"] = re.sub("^likes-post-\d+$",
                                                      "likes-post-32607564",
                                                      tooltipContent["id"], flags=re.MULTILINE)
                    likesSummary = tooltipContent.find("div", {"class": "likesSummary"}, recursive=False)
                    if likesSummary is not None:
                        LikeText = likesSummary.find("span", {"class": "LikeText"}, recursive=False)
                        if LikeText is not None:
                            LikeText.clear()  # gtfo lolz simps lol

    def solve(self, contestSoup: BeautifulSoup) -> Union[dict, None]:
        time.sleep(settings.solve_time)

        ContestCaptcha = contestSoup.find("div", class_="ContestCaptcha")
        if ContestCaptcha is None:
            self.puser.logger.warning("Couldn't get ContestCaptcha. Lag or contest is over?")
            return None

        messageContentCopy = copy.copy(contestSoup.find("div", {"class": "messageContent"}))
        self.hardenMessageContent(messageContentCopy)
        # i should honestly be using digest, but i'll leave it hexdigest for my own sanity
        result = hashlib.sha256(str(messageContentCopy).encode('utf-8')).hexdigest()
        if result not in known_hashes:
            self.puser.logger.critical("bad hash\n%s\n%s", result, messageContentCopy)
            Path("badhashes").mkdir(parents=True, exist_ok=True)
            with open(f"badhashes/{self.id}_{result}.html", "w") as f:
                f.write(str(contestSoup))
            raise RuntimeError("Unknown hash, please verify that nothing is wrong")
        self.puser.logger.info("Contest type %s, hash %s", known_hashes[result], result)
        # hardenMessageContent + hashing is gonna check for ["value"] and request_time. or at least i think so
        request_time = ContestCaptcha.find("input", {"name": "request_time"}, recursive=False)
        return {"request_time": request_time["value"]}  # returnval

    def onFailure(self, response):
        self.puser.logger.error("%d didn't participate (why lol?): %s", self.id, str(response))
        settings.ExpireBlacklist[self.id] = time.time() + 300000

    def onSuccess(self, response):
        self.puser.logger.debug("%s", str(response))
