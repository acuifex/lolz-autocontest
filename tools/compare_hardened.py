from bs4 import BeautifulSoup
import hashlib
import copy

import difflib

import os
# hack around my bad code
os.chdir("..")

# import solvers
from solvers import SolverFakeButton

def get_hardened(filename):
    with open("badhashes/"+filename, mode="r") as html:
        contestSoup = BeautifulSoup(html, "html.parser")
        messageContentCopy = copy.copy(contestSoup.find("div", {"class":"messageContent"}))
        SolverFakeButton.hardenMessageContent(messageContentCopy)
        print(hashlib.sha256(str(messageContentCopy).encode('utf-8')).hexdigest())
        # print(str(messageContentCopy))
        return str(messageContentCopy)

def main():
    first = get_hardened("4435626_0e1771d3c9d0edb0ef2c7c96208d0fe09e6123e5d10905d78dd7e36a4267fc12.html")
    second = get_hardened("4428216_1e1c6eae463b0f0c8311138b42580868473c559f920609a8171acb98e1a13790.html")
    # print(first)
    # print(second)
    diff = difflib.context_diff(first.split("\n"), second.split("\n"))
    print('\n'.join(diff))

if __name__ == '__main__':
    main()