import copy
import hashlib
import re
import time
from pathlib import Path
from typing import Union

from bs4 import BeautifulSoup, Tag

import settings

known_hashes = {
    "167687ad13a568966f87ed51ddfee1f729a03f2ea89b11f37db3622cf108633a": "",
    "9017896a1b7cc54316fd4328255b58d22e83341f6933490b0a548a82845ed3af": "week_likes_req",
    "7d18052395e0ea877f1c1b9770c6e0618fac991ed64f0a3fd379dedcdd7d59f1": "likes_req",
    "40f06ad252ec116ab8c9d9f467ede0f9a7ba6d316ef20c013bdea39d19aec3d9": "edited",
    "bb25f3ad3502ab02509e60f0f8eaf42aed0106be0e9514b9f3096ce129153663": "money",
    "afb0bb2b70294ac9665f7522a34b51704a6de35e49d76513986519932fca35ff": "multiple",
    "7538e7398af3fe5408c2dd6ace149becdc18797e82d6b83c5a1b31bddf17200e": "likes",
    "512fe7d4ac26d3a4f97ea12478717e42fc2624941949f4fcfe9b1c5ba7af47da": "week_likes_req likes_req",
    "6e542ceda4d1de256746df4f9830ef187d51eab684d50b69e49847843caf2fdc": "week_likes_req edited",
    "342dc5bbfa68f0528cc27c1e39c171c9ecccf446861f9c5082ba19e2f88c4ae4": "week_likes_req money",
    "75c31b8026f1c3ec2a7ea1f44df4628c609346cf6230e68ab3f95186382ab3a1": "week_likes_req multiple",
    "0cce52e513174871ac8f7e73a646be52d4347e325f694c657cef178abaa1b264": "week_likes_req likes",
    "f8d22c0a8ec6003334874fbef1f2e5be0b7d1e94810eb094794cb72412820723": "likes_req edited",
    "25e842f7b19ef941712b933bb41ba52b5e059a6a2f303195af7a084fc7f09d2d": "likes_req money",
    "afa36bdae26f403596aedb7521ccdc2baba2b9cb6e543dcd03f4d86097ee5038": "likes_req multiple",
    "9d46cf81592c061df6ba71778778e7a9a6d59d545e4f767d6523735bca8855c6": "likes_req likes",
    "4e7e4c46729899f65b97db9961b9ead16ab1e1e8e6da169e2f5c8c2b605e2fb7": "edited money",
    "d1de80c75ff4481451cea6ee1d2ad64be314a2f8b1da44b27d1e791e709c02bb": "edited multiple",
    "030d8f19be180fbe2b8e1d501e06669a1af800cf7241155dc5deed2177e5a553": "edited likes",
    "89543fd0d7d47200962d169b035d6bce3c2ac2eefaae69ab880adcd93b4c141a": "money multiple",
    "3270d14c432eff78a1994319b64c57693930e40aa5d9b4c7ed888300e0dacaae": "money likes",
    "a7188af50f718a6850c1ce391a3da779da9fed5393607a20fd2d74f67d3e5c6a": "multiple likes",
    "cb155e4121a4f40a93f584479080aa049997e3978e5db286cb1b7bebfe365723": "week_likes_req likes_req edited",
    "dc5bcb65fdf4f50b40a3d21badacc0bb526a8fa1d99f488f39f8dce2702b4619": "week_likes_req likes_req money",
    "947b80725ea0d3e3da3c1d24e69b1171a4aba404ec0fca9c3534fb69a575c386": "week_likes_req likes_req multiple",
    "77aafb83fa692e2e348cad50a11c06d5b9a587a7a25a9d4da1538d1f372ed7ff": "week_likes_req likes_req likes",
    "7e375cdadf339a135719cc0527102ebbecf381f5a1b9ff317512e476b32d6e67": "week_likes_req edited money",
    "648f2bfdbddacecdb61146154673e4688303eaca05219077b59f5300004ae2ed": "week_likes_req edited multiple",
    "b7b0ea93c4e636f00a042833590b269e97bdef8ffea140e862aca58a33bba97f": "week_likes_req edited likes",
    "074e861f1bca393743f89fc629ab9df2e6b8a7de1e22945097305b71021cca08": "week_likes_req money multiple",
    "627f7c3625b34773e431d33da39a99f9c136ea89992b73ed82ed3e3f2ee576e9": "week_likes_req money likes",
    "89921da34e21890d083450509f7890b34a1efda20790dd10fd004dd93ebb5eff": "week_likes_req multiple likes",
    "4c07663e52ee4fd2db9494d77b7838930c18964fa4c718a40959cccd43823cbb": "likes_req edited money",
    "9b7003baf7d59a0b4547aa4edb4b2154c1f31c0769372afbcbf2cb1a0ef280c6": "likes_req edited multiple",
    "8d480207fd8e332d4ded0653c573d51e3063e53ce4cab154b71bffc3b75d237e": "likes_req edited likes",
    "baaf23ed4cd118311f4443999da5578782f63d77c128ea9dcf9359b372f0ed35": "likes_req money multiple",
    "664dbdcd5633fc37644b682382029a2e27d5d2a69b92a50d7d9930753a6e3b52": "likes_req money likes",
    "7a7ebd9533dada747dc4e3b32be4d4672375dc0c6fea0c497ee87e53013045d6": "likes_req multiple likes",
    "518733777009d3106b03ad9e12cfbd2ddf38573ca4f88b0a085a5f0343d15f98": "edited money multiple",
    "67787e047dd74aca8fb1e64292d5220860f1400f8b09dfef33158463cd253475": "edited money likes",
    "e635d492995e0a57a73dc8f2ea8cb16803dab49b0d3af1d4cafaecc5fdd645ed": "edited multiple likes",
    "fba2b2056560cb10fe0943e4ffa0df2e0a90c386a8ec239f3c8a0b30e6f2ffb7": "money multiple likes",
    "84b78d0940ed34412f949cfca2916975be39fabe34fd726373849fd84202ae2d": "week_likes_req likes_req edited money",
    "da5ecfc20126317b3e785f47091b4d54c7498649e29ac968d4ea0ee605d048f8": "week_likes_req likes_req edited multiple",
    "e23dc8525ca9e4771771dd24a4b4b81dd6e7b931d5caac41a79b63fc4ebfafc1": "week_likes_req likes_req edited likes",
    "260c9a7b618310f221b2cfe3e21672166c1812aeca040e4263cedd13bfcab57d": "week_likes_req likes_req money multiple",
    "3661fb0aba5c2d84ff3ac85b2d6ef23e5222ed8382bd8438c099b1ea50001e5d": "week_likes_req likes_req money likes",
    "9aab636bb9a6a0e083a9e9fc8c9974e892b30e2a7d7c6994fc5a64a7b3a751b5": "week_likes_req likes_req multiple likes",
    "802474a1a9fa7da5c89476378c745f68008a0f9ceded343d6dda5e75206df93c": "week_likes_req edited money multiple",
    "74c83ed420117013151064ed2e90ee57c344b8b19976758060c84c5f9a9e2449": "week_likes_req edited money likes",
    "ddeee39a2c55c863374189df5bfac6217459098ce393e2e6b616bcafa1b8ea51": "week_likes_req edited multiple likes",
    "50065e71fa51a3602f552f6dcf349d858d15a822e9ecdb41def18105d16c04bd": "week_likes_req money multiple likes",
    "48f17da6135e89af56203abcd4365adf2a9afaf01d46b126a6c2c266e8451818": "likes_req edited money multiple",
    "868bb935912c3c436b2fc24b3aadbe3d45843edf5d627098c75ffd3274724e14": "likes_req edited money likes",
    "05bdfc75e05a3927d38c741ec787d752a7faf746c22e3bdfb7bf160fd1202089": "likes_req edited multiple likes",
    "8ee8961259c95e4ac6ae66bd7242f817f10822584439b374b0e99868963cc9ad": "likes_req money multiple likes",
    "b3c38b428e2c4b48ac731e62416e32aa49ba704c00d1c67abb86b48cbf3c5744": "edited money multiple likes",
    "531d39ed5a7c3a1596188449811285152f0ded71065370bac77ad75e8cd0ff2a": "week_likes_req likes_req edited money multiple",
    "dd5b97f19bf570b5b17fa36379881641f824401c85833b2a700e034a6afaf956": "week_likes_req likes_req edited money likes",
    "203e4154975177ab0a3078bd5406a05dd94439bff673df9c96128b6d7737bb72": "week_likes_req likes_req edited multiple likes",
    "0e1771d3c9d0edb0ef2c7c96208d0fe09e6123e5d10905d78dd7e36a4267fc12": "week_likes_req likes_req money multiple likes",
    "0915abcc1648e14d2cb4435f429c97e7fbb316ad00b4701c3d0af1eeeb92ff9c": "week_likes_req edited money multiple likes",
    "400b83a30cf8eb7c6fef2a1738a713e2ba21ec26e7577790f05f0e7b53d2e1a3": "likes_req edited money multiple likes",
    "cf830c6b33ff326d5119d6797f3e66e6bdba84a79650c20fb9a8a338f09fcab0": "week_likes_req likes_req edited money multiple likes",
    "4a6d4b65d7ac2825c17500680c4a0b3dd6f19755badb0d32f993f25fe97cc048": "",
    "3e33d8ff363e808033a8bf361c1f174a2adf024a082e088bb97d8799b3a0a5e0": "week_likes_req",
    "06e250663e76cde648b7782a8d1552346bbd2255f41dd632703a9b4988380f68": "likes_req",
    "384e7798f023cc5a5c0573de18c4d65fc211c0a6d340d1077b5f97b78144816a": "edited",
    "210173f803c17d00a34f90f72d0945e402106578a2bac8e5b55f6120bec76c24": "money",
    "f2d4018dc8e1ab40cdb29aa6bf3a2dc7ff4c4154b45df8fddf4f8b4f2ff8dab3": "multiple",
    "01bd3155a1cccfc4369a8ba8909ab71458b07185fa0014bd806a7432900fcb21": "likes",
    "3b1cc2fd6a1c919bb515f8e8a1a6a62b250c7ba21438693d4415ef2984b897a4": "week_likes_req likes_req",
    "beab9916ebedb0169e5fd40d9530d9d282a8c9d528d76737662014706c4d988f": "week_likes_req edited",
    "881533589efbc68f5c4e7df3f923ea6ab9ba18411916ce1bbb248dc41887f9c6": "week_likes_req money",
    "a6a7b8b1339fd5e41aae40bba1a99a61ab678f3da2c5339636f36551c62f2faf": "week_likes_req multiple",
    "9447340855564ea7318ab742a69308256d4f0a424904a551b948b82db4543518": "week_likes_req likes",
    "4125b9b236bdd3caa2addf235a026f9747d3bfbf71cd90da31bd6dc013e3e7f6": "likes_req edited",
    "511409b7bfc8c862d248b5353e461b85511c93eb20e49797817aff8f3e98c18d": "likes_req money",
    "e3cd4eed78de91eb8911224913f4138521c8a11b319c231a66ab7aa3a403b8d9": "likes_req multiple",
    "770af647d5e75022da61c8c4b8ed58a201e1abd1bdd0f20af9614a7a47729c1e": "likes_req likes",
    "2ccd741ac7483eea8c0051f301577eef0a85d03b9900e01e64660224b0e6088e": "edited money",
    "3b279f5f77d13a823f82781fc900243b797374dae95ab9afbd9727fa71bfccba": "edited multiple",
    "e22ed0b64f420b921154a373e74d0a8943eb555863dd38ab46e0162caa5cb4b6": "edited likes",
    "dc14229575fe872e89a5a8ff6faa14c569a1702e305f6bdf7147ce0b6e508fd8": "money multiple",
    "bb40b0a905fbb715c324ba30c3ad73867728ef08e237c50d41a99e39b9f57e80": "money likes",
    "d7df52164e864f27d408c4cec2a78e958ba8d53c01928b8126aa1d330f29ea83": "multiple likes",
    "d11465b52eb0849f843ad05753cf4d6b8ab547d5ab8c2e08453a034ac961e99c": "week_likes_req likes_req edited",
    "b3c5fbc354d251bce05a06daab09cd38a8cf2811d70cab2ef6b933c85def5bd7": "week_likes_req likes_req money",
    "2dc7b28a9d1fb59f5cc3f64d09b3c6e83935cf975eebd12d2672b3a342051605": "week_likes_req likes_req multiple",
    "864f281c3074cfa190bec51172237c394964038608c2e86ff0d74786e06939d0": "week_likes_req likes_req likes",
    "272819f013f24dc098027484b11ab329265de8def263b6e53c74f4c6a426fc2f": "week_likes_req edited money",
    "e44f9af48e9c89d805e2123cde6e216de79072b24937f6722ffb2282d7810316": "week_likes_req edited multiple",
    "beaec97c5849ddc8563da25daea0ef46c9731f277f8eac760f302f7539930ed3": "week_likes_req edited likes",
    "72a86cfd2deb47c8d2f0e8eb24e5de7be9148025db9ddd0dc2293ed6cf825c62": "week_likes_req money multiple",
    "c93a3f9782e78da8dbfa27be5143f9ebec52bb14968b0262f023374ed05e95c6": "week_likes_req money likes",
    "cf05dd9488b448f913f3691aeea09dbf0aa682a3d1d9fb575cc2f97c0d3017b4": "week_likes_req multiple likes",
    "f98158d88c8f568e2500d4949f13b38170d135453d53702aa45e9477b8b8df28": "likes_req edited money",
    "a9271436a5463bbb4f1584fe9970f51177fb2db20ad79fe315e8cb88ed490901": "likes_req edited multiple",
    "2eb818c6e8e447a627a752082af0f8faaf8af3a5760d91a2da5a1610327cb2fb": "likes_req edited likes",
    "bcc5470382221a75d2f183fcde4c34da31cc80a44d1bc3b2141360f4f1809d86": "likes_req money multiple",
    "1328348d1a7a56c744da92299c55b1a30d7688a18078d7cdd66d7356d49b2ffc": "likes_req money likes",
    "8cf5184b74b0ef7324656224e7f76c3db9446b9566f2a0018f7608997caca55c": "likes_req multiple likes",
    "e834dc3db8c551f0c61a86dcf91187d4b2c8867a5466ea6808923fe1afe635c0": "edited money multiple",
    "400142f6c0ddfda579a034af73490a427331e7168d17519384b5bee2860505a1": "edited money likes",
    "065719f92f714b20275dddd55050b8728b815126799ca0f4cf3e4bab3f7a2c9e": "edited multiple likes",
    "7eddfce84b8e86eff974299f596bd3afdadb5e0b78bb4fb784902accee1c729d": "money multiple likes",
    "639dd2a6def72626c832491efc9aa2e3cd4092a60408b4b0c9c0cb1966f9b8f8": "week_likes_req likes_req edited money",
    "9f0db345d4a08d16b8f7142c0283000a3e1f507cb1e9bbaf10459f15ca8ac492": "week_likes_req likes_req edited multiple",
    "7ab9a4cc2b381de50185b84915c1d71c37dd4535c9f960b2601c0bc6c81dfb1f": "week_likes_req likes_req edited likes",
    "e9e48d2c2bfde6beb31407082060feadce68fa9cacc633526d54fa6e957ed3aa": "week_likes_req likes_req money multiple",
    "6b6b50b876cb7ac612021610fd13cd93b6b734ad801d34f93373dbe3b47f2dc2": "week_likes_req likes_req money likes",
    "d6c52bcfbb15fa792f303a6b194a10dae31f228d1ab6f2e6c30e8fbad0c3d240": "week_likes_req likes_req multiple likes",
    "019900294cc011830f95c1d60557ffa4f677d01b7861019b227b31f3a009331a": "week_likes_req edited money multiple",
    "7213e3892c21011560ce34978e1a9048b62f79e8871deff4076ff74861b418d8": "week_likes_req edited money likes",
    "db9238c8edd99d8a24f531e5c2537550a6b20846bc28f0175cff93f860cc9292": "week_likes_req edited multiple likes",
    "646151aebd8968803f48e05e7c7b19f6b0e00cfbff0704c5579021cc8ba339b5": "week_likes_req money multiple likes",
    "5ae65e98e8ed0990f6f688c0b889a041b051c965c278de6f235dcbfaa64eac56": "likes_req edited money multiple",
    "5f7febf7931025a5edd5512007d3b0c459ba6748924e462690529d029f07ff91": "likes_req edited money likes",
    "9221db1258a46b0c0bb21aa26531a805bfa48a120efe22312e41dd7dec0af137": "likes_req edited multiple likes",
    "de317c7ac4af16fba0e1f11de0717830669771cf6580c2415492834099030480": "likes_req money multiple likes",
    "8371d07ce8ad7a2f438e848ebb94fb90e59900337ad5299c926fea3cbcb347dd": "edited money multiple likes",
    "db6b03c967b18dcde3e80e18221a79e54967258ad1d941ccba7642c6b032798d": "week_likes_req likes_req edited money multiple",
    "6da54c99814385049926e0871f865648a576a7ef9930071af503d307e9910b9b": "week_likes_req likes_req edited money likes",
    "d2e490769675acfa0726738827ca56aa701fe3860a5ff9e7df479b62ab1c2ac5": "week_likes_req likes_req edited multiple likes",
    "54bd5174b3f0b3a484fa1acc760f136890372d27e7cb45f36f148e4221c74954": "week_likes_req likes_req money multiple likes",
    "c811b0f49b3d7a19209a1d4f65b4b14a6b67beb417b1583dccdcd161019dd460": "week_likes_req edited money multiple likes",
    "20b94d44a99a0507714a986fc9ea40184a8e18d8525ca64ca4ce8d55c827b10c": "likes_req edited money multiple likes",
    "2c593b80777dd877a8ffb708b203a84c47aa7cf1a8ea866dfc105205b0e0a990": "week_likes_req likes_req edited money multiple likes",

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
    @staticmethod
    def hardenContestInfo(soupMarginBlock: Tag):
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
    @staticmethod
    def hardenMessageContent(soupMessageContent: Tag):
        article = soupMessageContent.find("article", recursive=False)
        if article is not None:
            usercontent = article.find("blockquote", {"class": "messageText SelectQuoteContainer baseHtml ugc"},
                                       recursive=False)
            if usercontent is not None:
                usercontent.clear()  # nuke all user content
            contestThreadBlock = article.find("div", {"class": "contestThreadBlock"}, recursive=False)
            if contestThreadBlock is not None:
                for captchainfo in contestThreadBlock.find_all("div", {"class": "marginBlock"}, recursive=False):
                    SolverFakeButton.hardenContestInfo(captchainfo)
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

        translate = soupMessageContent.find("span", {"class": "TranslateButton button mn-15-0-0"}, recursive=False)
        if translate is not None:
            # looks dumb as hell, but whatever
            if re.match("""<span class="TranslateButton button mn-15-0-0" data-href="posts/\d+/translate\?language_id=\d+">
				Перевести на Русский
			</span>""", str(translate), flags=re.MULTILINE):
                if translate.next_sibling == "\n":
                    translate.next_sibling.extract()
                translate.extract()
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

                likesLink = publicControls.find(re.compile("^(span|a)$", flags=re.MULTILINE),
                                                {"class": re.compile("(?:Tooltip PopupTooltip )?LikeLink item control like"),
                                                 "data-content": ".TooltipContent"}, recursive=False)
                if likesLink is not None:
                    # TODO: this is kinda a bandaid fix for limited/unlimited accounts, but it'll have to do for now
                    likesLink.name = "span"
                    if likesLink.get("href") is not None:
                        if re.match("^posts/\d+/like$", likesLink["href"], flags=re.MULTILINE):
                            del likesLink["href"]
                        # likesLink["href"] = re.sub("^posts/\d+/like$",
                        #                            "posts/32607564/like",
                        #                            likesLink["href"], flags=re.MULTILINE)
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
                        likeLabel.string = re.sub("^\d*$", "42", str(likeLabel.string or ''), flags=re.MULTILINE)
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

        messageContent = contestSoup.find("div", {"class": "messageContent"})

        # TODO: this looks ugly.
        contestThreadBlock = messageContent.find("div", {"class": "contestThreadBlock"})
        if contestThreadBlock is not None:
            for captchainfo in contestThreadBlock.find_all("div", {"class": "marginBlock"}, recursive=False):
                # https://youtu.be/FBdFhgWYEjM
                if re.match("\s*Приз:\s+Слив фотографий", captchainfo.text):
                    settings.ExpireBlacklist[self.id] = time.time() + 30000000000
                    self.puser.logger.notice("saved your ass from a useless contest")
                    return None

        if settings.check_hash:
            messageContentCopy = copy.copy(messageContent)
            SolverFakeButton.hardenMessageContent(messageContentCopy)
            # i should honestly be using digest, but i'll leave it hexdigest for my own sanity
            result = hashlib.sha256(str(messageContentCopy).encode('utf-8')).hexdigest()
            if result not in known_hashes:
                self.puser.logger.critical("bad hash\n%s\n%s", result, messageContentCopy)
                Path("badhashes").mkdir(parents=True, exist_ok=True)
                # windows users can't have nice standards smh
                with open(f"badhashes/{self.id}_{result}.html", "w", encoding="utf-8") as f:
                    f.write(str(contestSoup))
                # TODO: handle bad hashes instead of raising runtime exception.
                raise RuntimeError("Unknown hash, please verify that nothing is wrong")
            self.puser.logger.info("Contest tags \"%s\", hash %s", known_hashes[result], result)

        request_time = ContestCaptcha.find("input", {"name": "request_time"}, recursive=False)
        if request_time is None:
            self.puser.logger.warning("request_time is missing.")
            return None
        return {"request_time": request_time["value"]}  # returnval

    def onFailure(self, response):
        self.puser.logger.error("%d didn't participate (why lol?): %s", self.id, str(response))
        settings.ExpireBlacklist[self.id] = time.time() + 300000

    def onSuccess(self, response):
        self.puser.logger.debug("%s", str(response))
