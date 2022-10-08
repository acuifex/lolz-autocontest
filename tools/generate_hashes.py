import re

from bs4 import BeautifulSoup, Tag
import hashlib
import copy
import itertools

import difflib

import os
# hack around my bad code
os.chdir("..")

from solvers import SolverFakeButton

def extract_with_newline(Soup: Tag):
    if Soup.next_sibling == "\n":
        Soup.next_sibling.extract()
    Soup.extract()

def remove_total_likes_requirement(Soup: Tag):
    for captchainfo in Soup.find_all("div", {"class": "marginBlock"}):
        if re.match("\s*Необходимо набрать за 7 дней \d+ симп\w{0,8}",captchainfo.text):
            extract_with_newline(captchainfo)
def remove_weekly_likes_requirement(Soup: Tag):
    for captchainfo in Soup.find_all("div", {"class": "marginBlock"}):
        if re.match("\s*Необходимо набрать за все время \d+ симп\w{0,8}", captchainfo.text):
            extract_with_newline(captchainfo)

def remove_money(Soup: Tag):
    for captchainfo in Soup.find_all("div", {"class": "marginBlock"}):
        if re.match("\s*Приз:\s+Деньги\s+\(\d+ ₽(?: x \d+)?\)",captchainfo.text):
            extract_with_newline(captchainfo)

def remove_multiple(Soup: Tag):
    for captchainfo in Soup.find_all("div", {"class": "marginBlock"}):
        if re.match("\s*Количество призов: \d+",captchainfo.text):
            extract_with_newline(captchainfo)

def remove_edited(Soup: Tag):
    changed = Soup.find("span", {"class": "item muted hiddenNarrowUnder"})
    if changed is not None:
        changedtooltip = changed.find("span",
                                      {
                                          "class": "Tooltip",
                                          "title": re.compile("^Отредактировал .+$", flags=re.MULTILINE)
                                      }, recursive=False)
        if changedtooltip is not None:
            if re.match("^\s*Изменено\s*$", changedtooltip.text, flags=re.MULTILINE):
                extract_with_newline(changed)
    pass

def remove_likes(Soup: Tag):
    publicControls = Soup.find("div", {"class": "publicControls"})

    button = publicControls.find(re.compile("^(span|a)$", flags=re.MULTILINE),
                                                {"class": re.compile("(?:Tooltip PopupTooltip )?LikeLink item control like"),
                                                 "data-content": ".TooltipContent"}, recursive=False)
    if "Tooltip" in button["class"]:
        button["class"].remove("Tooltip")
    if "PopupTooltip" in button["class"]:
        button["class"].remove("PopupTooltip")

    likeLabel = button.find("span", {"class": "LikeLabel"}, recursive=False)
    likeLabel.string = ""
    tooltipContent = publicControls.find("div", {"class": "TooltipContent"}, recursive=False)
    if tooltipContent is not None:
        extract_with_newline(tooltipContent)

def remove_all(contestSoup: Tag):
    remove_total_likes_requirement(contestSoup)
    remove_weekly_likes_requirement(contestSoup)
    remove_edited(contestSoup)
    remove_money(contestSoup)
    remove_multiple(contestSoup)
    remove_likes(contestSoup)

def add_total_likes_requirement(Soup: Tag):
    addSoup = BeautifulSoup("""<div class="marginBlock">
<span class="info-separator m-right"></span>Необходимо набрать за все время 1 симпатию
			</div>
    """, 'html.parser')
    for captchainfo in Soup.find_all("div", {"class": "marginBlock"}):
        if re.match("\s*Бот выбирает победителей случайным образом\.",captchainfo.text):
            captchainfo.insert_before(addSoup)
            break

def add_weekly_likes_requirement(Soup: Tag):
    addSoup = BeautifulSoup("""<div class="marginBlock">
<span class="info-separator m-right"></span>Необходимо набрать за 7 дней 1 симпатию
			</div>
    """, 'html.parser')
    for captchainfo in Soup.find_all("div", {"class": "marginBlock"}):
        if re.match("\s*Бот выбирает победителей случайным образом\.",captchainfo.text):
            captchainfo.insert_before(addSoup)
            break

def add_money(Soup: Tag):
    addSoup = BeautifulSoup("""
    <div class="marginBlock">
<span class="info-separator m-right"></span><span>Приз:</span>
<span class="bold">
					Деньги
					
						
						(300 ₽)
						
						
						
					
					
				</span>
</div>""", 'html.parser')
    for captchainfo in Soup.find_all("div", {"class": "marginBlock"}):
        if re.match("\s*Приняли участие: \d+ пользовате\w{0,6}",captchainfo.text):
            captchainfo.insert_after(addSoup)
            break

def add_multiple(Soup: Tag):
    addSoup = BeautifulSoup("""
<div class="marginBlock">
<span class="info-separator m-right"></span><span>Количество призов:</span> 2
			</div>""", 'html.parser')
    for captchainfo in Soup.find_all("div", {"class": "marginBlock"}):
        if re.match("\s*Приняли участие: \d+ пользовате\w{0,6}",captchainfo.text):
            captchainfo.insert_after(addSoup)
            break

def add_edit(Soup: Tag):
    addSoup = BeautifulSoup("""<span class="item muted hiddenNarrowUnder">
<span class="Tooltip" title="Отредактировал acuifex 1 мин. назад">
							Изменено
							</span>
</span>
    """, 'html.parser')
    Soup.find("div", {"class": "privateControls"}).append(addSoup)

def add_likes(Soup: Tag):
    publicControls = Soup.find("div", {"class": "publicControls"})

    button = publicControls.find(re.compile("^(span|a)$", flags=re.MULTILINE),
                                                {"class": re.compile("LikeLink item control like"),
                                                 "data-content": ".TooltipContent"}, recursive=False)
    # insert does some goofy ahh shit. let's just not bother...
    # button["class"].insert(0, "PopupTooltip")
    # button["class"].insert(0, "Tooltip")
    button["class"] = "Tooltip PopupTooltip LikeLink item control like"

    likeLabel = button.find("span", {"class": "LikeLabel"}, recursive=False)
    likeLabel.string = "42"

    addSoup = BeautifulSoup("""<div class="TooltipContent" id="likes-post-32840696">
<div class="likesSummary">
<span class="LikeText">
<a class="username" dir="auto" href="members/2663422/"><span class="style65">samogon</span></a>, <a class="username" dir="auto" href="members/5359421/"><span class="style22">SheykeR</span></a>, <a class="username" dir="auto" href="members/2434158/"><span class="style22">MOFG</span></a> и <a class="OverlayTrigger" href="posts/32840696/likes">2 другим</a> нравится это.
			
			
			
		</span>
</div>
</div>
</div>""", 'html.parser')
    publicControls.append(addSoup)

add_dict = {
    "week_likes_req": add_weekly_likes_requirement, # weekly must go first
    "likes_req": add_total_likes_requirement,
    "edited": add_edit,
    "money": add_money,
    "multiple": add_multiple,  # NOTE: must be after money, because they both add after contender count
    "likes": add_likes,
}

# destructive!
def get_hash(messageContent: Tag):
    SolverFakeButton.hardenMessageContent(messageContent)
    return hashlib.sha256(str(messageContent).encode('utf-8')).hexdigest()

# debug functions:
def harden_compare(a, b):
    messageContentCopy = copy.copy(a)
    SolverFakeButton.hardenMessageContent(messageContentCopy)
    messageContentCopy2 = copy.copy(b)
    SolverFakeButton.hardenMessageContent(messageContentCopy2)
    diff = difflib.context_diff(str(messageContentCopy).split("\n"), str(messageContentCopy2).split("\n"))
    print('\n'.join(diff))

def compare(a, b):
    diff = difflib.context_diff(str(a).split("\n"), str(b).split("\n"))
    print('\n'.join(diff))

def main():
    base_file = "4435626_0e1771d3c9d0edb0ef2c7c96208d0fe09e6123e5d10905d78dd7e36a4267fc12.html"
    with open("badhashes/" + base_file, mode="r") as html:
        contestSoup = BeautifulSoup(html, "html.parser")
        messageContent = contestSoup.find("div", {"class": "messageContent"})
        remove_all(messageContent)
        # print(str(messageContent))
        # https://stackoverflow.com/a/5898031
        for L in range(len(add_dict.items()) + 1):
            for subset in itertools.combinations(add_dict.items(), L):
                messageContentcopy = copy.copy(messageContent)
                name = ""
                for i in subset:
                    name += i[0] + " "
                    # "'str' object is not callable" lol, dum intellij
                    i[1](messageContentcopy)
                hash = get_hash(copy.copy(messageContentcopy))
                # if hash == "db6b03c967b18dcde3e80e18221a79e54967258ad1d941ccba7642c6b032798d":
                #     print(str(messageContentcopy.find("div", {"class": "publicControls"})))
                # TODO: improve name output
                print(f'"{hash}": "{name.rstrip(" ")}",')

        # messageContentcopy = copy.copy(messageContent)
        # before = copy.copy(messageContentcopy)
        # remove_total_likes_requirement(messageContentcopy)
        # remove_weekly_likes_requirement(messageContentcopy)
        # add_weekly_likes_requirement(messageContentcopy)
        # add_total_likes_requirement(messageContentcopy)
        # after = copy.copy(messageContentcopy)
        # compare(before, after)

if __name__ == '__main__':
    main()