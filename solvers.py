import re
from typing import Tuple, Union
from PIL import Image, ImageFilter
import numpy as np
import io
import mmh3
import struct
import base64

import settings

pattern_captcha_sid = re.compile(r"sid\s*:\s*'([0-9a-f]{32})'", re.MULTILINE)
pattern_captcha_dot = re.compile(r'XenForo.ClickCaptcha.dotSize\s*=\s*(\d+);', re.MULTILINE)
pattern_captcha_img = re.compile(r'XenForo.ClickCaptcha.imgData\s*=\s*"([A-Za-z0-9+/=]+)";', re.MULTILINE)


class SolverSlider2:
    def __init__(self, puser):
        self.puser = puser

    def applyencryption(self, key: int, data: bytes) -> bytes:
        out = io.BytesIO()
        for i in data:
            out.write((i ^ (key & 0xff)).to_bytes(1, byteorder='big'))
            uVar3 = (key >> 1) & 0x7fff
            uVar6 = key & 1
            key = uVar3 ^ 0xffffb400
            if uVar6 == 0:
                key = uVar3
        out.seek(0)
        return out.read()

    def requestcaptcha(self, sid: bytes) -> Union[Tuple[int, bytes, bytes, int], None]:
        response = self.puser.makerequest("POST", "https://captcha." + settings.lolzdomain + "/captcha",
                                          headers={'referer': "https://lolz.guru/",
                                                   'origin': "https://lolz.guru"}, cookies={}, data=sid,
                                          timeout_eventlet=15, timeout=12.05, retries=3, checkforjs=False)

        if response is None:
            return None

        datahash = mmh3.hash(response.content[0x15:], 0xf0e8, False)

        # struct: hack_me_if_you_can\n, short, payload
        key = struct.unpack("H", bytes(response.content[0x13:0x13 + 2]))[0] ^ 0x5c37
        decrypted = self.applyencryption(key, bytes(response.content[0x13 + 2:]))

        # struct: 0x00, int1, int2, int3, png of size int1, png of size int2
        imgsize1, imgsize2, y = struct.unpack("III", decrypted[1:1 + struct.calcsize("III")])
        return y, decrypted[13:13 + imgsize1], decrypted[13 + imgsize1:13 + imgsize1 + imgsize2], datahash

    def sendsolution(self, sid: bytes, datahash: int, x: int) -> Union[int, None]:
        # works without captcha start -> captcha end path but doesn't work without start -> capctha start
        # ehh whatever it'll look more realistic on the server anyway
        # TODO: make like an actual random path generator so it's even more realistic
        tmp = bytes.fromhex(
            "0288000000AD0100000288000000AE0100000287000000AE0100000287000000AF0100000287000000B00100000287000000B10100000287000000B20100000286000000B30100000286000000B40100000286000000B50100000286000000B60100000286000000B70100000286000000B80100000286000000B90100000286000000BA0100000286000000BB0100000286000000BC0100000286000000BD0100000286000000BE0100000286000000BF0100000285000000C00100000285000000C10100000285000000C20100000285000000C30100000285000000C40100000284000000C40100000284000000C50100000283000000C60100000283000000C70100000283000000C80100000283000000C90100000282000000C90100000282000000CA0100000282000000CB0100000281000000CB0100000281000000CC0100000281000000CD0100000281000000CE0100000281000000CF0100000281000000D00100000281000000D10100000281000000D20100000281000000D30100000281000000D40100000281000000D50100000281000000D60100000281000000D70100000282000000D70100000282000000D80100000282000000D90100000282000000DA0100000281000000DA0100000281000000DB0100000280000000DB010000027F000000DB010000027E000000DB010000027E000000DC010000027D000000DC010000027D000000DD010000027C000000DD010000027B000000DD010000027A000000DD0100000279000000DE0100000278000000DE0100000277000000DE0100000277000000DF010000")
        tmp += struct.pack("<Bii", 0x00, 119, 481)
        for i in range(x):
            tmp += struct.pack("<Bii", 0x02, 119 + i, 481)
        tmp += struct.pack("<Bii", 0x01, 119 + x, 481)
        encrypted = self.applyencryption(datahash & 0xffff, tmp)

        requestdata = b"hack_me_if_you_can\n" + sid + encrypted

        response = self.puser.makerequest("POST", "https://captcha." + settings.lolzdomain + "/captcha",
                                          headers={'referer': "https://lolz.guru/",
                                                   'origin': "https://lolz.guru"}, cookies={}, data=requestdata,
                                          timeout_eventlet=15, timeout=12.05, retries=3, checkforjs=False)

        if response is None:
            return None

        return int.from_bytes(response.content, byteorder='little')

    def solve(self, captchaBlockSoup) -> Union[dict, None]:
        captchahash = captchaBlockSoup.find("input", attrs={"name": "captcha_hash"}).get("value")
        # TODO: more checks here?
        scriptcaptcha = captchaBlockSoup.find("script")
        sidMatch = pattern_captcha_sid.search(scriptcaptcha.string).group(1)
        self.puser.logger.debug("sid: %s", sidMatch)
        sid = int(sidMatch, 16).to_bytes(16, byteorder="big")

        captcharesponse = self.requestcaptcha(sid)
        if captcharesponse is None:
            return None

        y, captcha, puzzle, datahash = captcharesponse
        self.puser.logger.debug("hash: %d", datahash)
        if y > 170 or y < 0:
            self.puser.logger.error("y value from captcha response is invalid: %d", y)
            return None

        x, diff = self.findPuzzlePosition(captcha, puzzle, y)
        self.puser.logger.debug("solved x,y: %d,%d diff: %.2f", x, y, diff)

        solutionResponse = self.sendsolution(sid, datahash, x)
        if solutionResponse is None:
            return None

        # TODO: somehow fail if solutionResponse is 0?
        self.puser.logger.verbose("send solution response is: %d", solutionResponse)
        if settings.save_error_images and solutionResponse == 0:
            with open(settings.imagesDir + '{0:X}_{0:d}_captcha.png'.format(datahash, y), 'wb') as file:
                file.write(captcha)
            with open(settings.imagesDir + '{0:X}_{0:d}_puzzle.png'.format(datahash, y), 'wb') as file:
                file.write(puzzle)

        return {
            'captcha_hash': captchahash,
            'captcha_type': "Slider2Captcha",
        }

    def findPuzzlePosition(self, captcha: bytes, puzzle: bytes, y: int):
        img = Image.open(io.BytesIO(captcha))

        # builtins.OSError: image file is truncated
        # why are you like this
        img = img.filter(ImageFilter.Kernel(size=(3, 3), kernel=(
            0, 1, 0,
            1, -4, 1,
            0, 1, 0
        ), scale=1))
        img = img.crop((0, y, img.size[0], y + 30))
        captcha = np.asarray(img).sum(axis=0)

        # img.show()
        #
        # w = np.asarray(img)
        # w = w.sum(axis=0)
        # w = w * ( 255 / w.max())
        # w = w.reshape((1, 300, 3))
        # img2 = Image.fromarray(w.astype(np.uint8))
        # img2.show()

        puzzle = np.asarray(Image.open(io.BytesIO(puzzle)).convert("RGB")).sum(axis=0)
        bestx = 0
        leastdiff = 2147483647  # basically maxint, 999999 would work too but meh
        # difflist = []
        for x in range(0, captcha.shape[0] - 30):
            diffarr = np.average(np.abs(np.subtract(captcha[x:x + 30], puzzle, dtype="int64")), 1)
            diff = np.mean(diffarr)
            # difflist.append(diff)
            if diff < leastdiff:
                bestx = x
                leastdiff = diff
            pass

        # asfd = np.array(difflist)
        # asfd = asfd - asfd.min()
        # asfd = asfd * ( 255 / asfd.max())
        # asfd = asfd.reshape((1, 270))
        # img2 = Image.fromarray(asfd.astype(np.uint8))
        # img2.show()

        return bestx, leastdiff

# mask of a circle. i know that this is suboptimal
# non gray are required while gray are "optional" if you can say so
isgray_mask = (
    (True, True, True, True, True, True, True, True, True, True, False, True, True, True, True, True, True, True, True, True, True),
    (True, True, True, True, True, True, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True),
    (True, True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True),
    (True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True, True),
    (True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True, True),
    (True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True),
    (True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True),
    (True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True, True),
    (True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, True, True),
    (True, True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True),
    (True, True, True, True, True, True, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True),
    (True, True, True, True, True, True, True, True, True, True, False, True, True, True, True, True, True, True, True, True, True)
)
total_grays = sum(x.count(True) for x in isgray_mask)
total_reds = sum(x.count(False) for x in isgray_mask)

class SolverHalfCircle:
    def __init__(self, puser):
        self.puser = puser


    def solve(self, captchaBlockSoup) -> Union[dict, None]:
        captchahash = captchaBlockSoup.find("input", attrs={"name": "captcha_hash"}).get("value")
        scriptcaptcha = captchaBlockSoup.find("script")
        dot = int(pattern_captcha_dot.search(scriptcaptcha.string).group(1))
        if dot != 20:
            self.puser.logger.critical("dotsize isn't 20 but instead is %d. Exiting", dot)
            raise RuntimeError

        img = pattern_captcha_img.search(scriptcaptcha.string).group(1)
        x, y, confidence = self.findCirclePosition(img)
        self.puser.logger.debug("solved x,y: %d,%d confidence: %.2f", x, y, confidence)
        return {
            'captcha_hash': captchahash,
            'captcha_type': "ClickCaptcha",
            'x': x,
            'y': y,
        }

    def findCirclePosition(self, captchab64: str) -> Tuple[int, int, float]:
        img = Image.open(io.BytesIO(base64.b64decode(captchab64)))
        pixels = img.load()
        bestx = besty = 0
        bestconfidence = 0
        for tiley in range(0, img.size[1], 20):
            for tilex in range(0, img.size[0], 20):
                gray_count = 0  # counts the amount of correct color outside the circle
                red_count = 0  # counts the amount of correct color inside the circle
                junk_in_red_count = 0  # counts the amount of non red and non gray inside the circle
                for x in range(21):
                    for y in range(21):
                        if tiley + y >= 200 or tilex + x >= 240:  # if out of bounds, just assume it's correct
                            if isgray_mask[x][y]:
                                gray_count += 1
                            else:
                                red_count += 1  # this is probably bad, this will create up to 2 incorrect pixels!!! fight me about it
                            continue

                        if isgray_mask[x][y]:
                            gray_count += 1 if 0xff not in pixels[x + tilex, y + tiley] else 0
                        else:
                            red_count += 1 if 0xff in pixels[x + tilex, y + tiley] else 0
                            junk_in_red_count += 1 if 0xff not in pixels[x + tilex, y + tiley] and pixels[
                                x + tilex, y + tiley] != (0x40, 0x40, 0x40) else 0
                confidence = abs(junk_in_red_count * 0.3 + red_count - total_reds / 2) * -1 + gray_count * 1.6
                # 0.3, -1 and 1.6 are the weights, negative weight means smaller the number - better
                if bestconfidence < confidence:
                    bestconfidence = confidence
                    bestx, besty = tilex, tiley
        return int(bestx / 20), int(besty / 20), bestconfidence