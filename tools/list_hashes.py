from bs4 import BeautifulSoup
import hashlib
import copy

import os
# hack around my bad code
os.chdir("..")

from solvers import SolverFakeButton, known_hashes

def main():
    directory = os.fsencode("badhashes")

    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if not filename.endswith(".html"):
            print("not html:", filename)
            continue
        with open(os.path.join("badhashes", filename), mode="r") as html:
            contestSoup = BeautifulSoup(html, "html.parser")
            messageContentCopy = copy.copy(contestSoup.find("div", {"class": "messageContent"}))
            SolverFakeButton.hardenMessageContent(messageContentCopy)
            result = hashlib.sha256(str(messageContentCopy).encode('utf-8')).hexdigest()
            if result not in known_hashes:
                print(f"{filename} unknown hash: {result}")
            else:
                print(f"{filename}:\n - Contest type {known_hashes[result]}, hash {result}")



if __name__ == '__main__':
    main()