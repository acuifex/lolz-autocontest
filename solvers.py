import re
from typing import Tuple, Union
from PIL import Image, ImageFilter
import numpy as np
import io
import mmh3
import struct
import base64
import time
import random

import settings

pattern_captcha_sid = re.compile(r"sid\s*:\s*'([0-9a-f]{32})'", re.MULTILINE)
pattern_captcha_dot = re.compile(r'XenForo.ClickCaptcha.dotSize\s*=\s*(\d+);', re.MULTILINE)
pattern_captcha_img = re.compile(r'XenForo.ClickCaptcha.imgData\s*=\s*"([A-Za-z0-9+/=]+)";', re.MULTILINE)

# TODO: make like an actual random path generator so it's even more realistic
slider_path = ((0x02, 0x0000022A, 0x0000011E, 0),
               (0x02, 0x0000022A, 0x000000E2, 12),
               (0x02, 0x0000022B, 0x000000D8, 25),
               (0x02, 0x00000231, 0x000000BD, 38),
               (0x02, 0x00000238, 0x000000A4, 51),
               (0x02, 0x0000023C, 0x00000097, 65),
               (0x02, 0x0000023D, 0x00000093, 77),
               (0x02, 0x00000237, 0x00000093, 841),
               (0x02, 0x0000022E, 0x00000092, 853),
               (0x02, 0x00000226, 0x00000092, 866),
               (0x02, 0x00000221, 0x00000093, 880),
               (0x02, 0x0000021D, 0x00000094, 891),
               (0x02, 0x0000021C, 0x00000094, 904),
               (0x02, 0x0000021B, 0x00000096, 1039),
               (0x02, 0x00000219, 0x00000098, 1052),
               (0x02, 0x00000217, 0x0000009B, 1065),
               (0x02, 0x00000213, 0x0000009E, 1077),
               (0x02, 0x0000020D, 0x000000A1, 1092),
               (0x02, 0x00000205, 0x000000A6, 1104),
               (0x02, 0x000001FE, 0x000000AB, 1117),
               (0x02, 0x000001F5, 0x000000AF, 1132),
               (0x02, 0x000001EE, 0x000000B1, 1145),
               (0x02, 0x000001E6, 0x000000B5, 1157),
               (0x02, 0x000001DE, 0x000000B6, 1172),
               (0x02, 0x000001D9, 0x000000B7, 1183),
               (0x02, 0x000001D4, 0x000000B9, 1198),
               (0x02, 0x000001D1, 0x000000BA, 1210),
               (0x02, 0x000001CE, 0x000000BD, 1224),
               (0x02, 0x000001C9, 0x000000BE, 1237),
               (0x02, 0x000001C2, 0x000000C1, 1252),
               (0x02, 0x000001BA, 0x000000C4, 1264),
               (0x02, 0x000001B1, 0x000000C7, 1277),
               (0x02, 0x0000019E, 0x000000CC, 1290),
               (0x02, 0x00000189, 0x000000D1, 1303),
               (0x02, 0x0000016E, 0x000000D8, 1317),
               (0x02, 0x0000014D, 0x000000E0, 1330),
               (0x02, 0x00000133, 0x000000E4, 1344),
               (0x02, 0x0000011F, 0x000000E7, 1357),
               (0x02, 0x00000115, 0x000000E9, 1371),
               (0x02, 0x0000010E, 0x000000EB, 1385),
               (0x02, 0x0000010A, 0x000000ED, 1397),
               (0x02, 0x00000107, 0x000000F0, 1411),
               (0x02, 0x00000102, 0x000000F5, 1423),
               (0x02, 0x000000FD, 0x000000F8, 1437),
               (0x02, 0x000000F5, 0x000000FD, 1451),
               (0x02, 0x000000ED, 0x00000102, 1466),
               (0x02, 0x000000E8, 0x00000106, 1478),
               (0x02, 0x000000E2, 0x00000109, 1491),
               (0x02, 0x000000E0, 0x0000010C, 1505),
               (0x02, 0x000000DE, 0x00000110, 1517),
               (0x02, 0x000000DD, 0x00000112, 1531),
               (0x02, 0x000000DD, 0x00000114, 1545),
               (0x02, 0x000000DC, 0x00000116, 1558),
               (0x02, 0x000000DC, 0x00000117, 1570),
               (0x02, 0x000000DB, 0x00000117, 1744),
               (0x02, 0x000000DA, 0x00000117, 1757),
               (0x02, 0x000000D9, 0x00000116, 1770),
               (0x02, 0x000000D7, 0x00000116, 1783),
               (0x02, 0x000000D6, 0x00000115, 1796),
               (0x02, 0x000000D5, 0x00000115, 1810),
               (0x00, 0x000000D5, 0x00000115, 1910),)


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
        current_time_ms = int(time.time() * 1000)

        last_entry = list(slider_path[-1])
        # hardcoded mouse movement is for 1280x1024
        last_entry[1] = int((last_entry[1] / 1280) * self.puser.monitor_dims[0])
        last_entry[2] = int((last_entry[2] / 1024) * self.puser.monitor_dims[1])

        tmp = b""
        for i in slider_path:
            tmp += struct.pack("<BiiQ", i[0],
                               int((i[1] / 1280) * self.puser.monitor_dims[0]),
                               int((i[2] / 1024) * self.puser.monitor_dims[1]),
                               i[3] + current_time_ms)
        # total time in ms that the slide is gonna tame
        total_time = int(random.uniform(1, 2.5) * 1000)  # use random int instead lol?
        for i in range(x):
            tmp += struct.pack("<BiiQ",
                               0x02,
                               last_entry[1] + i,
                               last_entry[2],
                               last_entry[3] + current_time_ms + int((total_time / x) * i) + 100)

        tmp += struct.pack("<BiiQ", 0x01,
                           last_entry[1] + x,
                           last_entry[2],
                           last_entry[3] + current_time_ms + total_time + 200)
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

        captcharesponse = self.requestcaptcha(
            sid + struct.pack("<ii", self.puser.monitor_dims[0], self.puser.monitor_dims[1]))
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
            with open(settings.imagesDir + '{:X}_{:d}_captcha.png'.format(datahash, y), 'wb') as file:
                file.write(captcha)
            with open(settings.imagesDir + '{:X}_{:d}_puzzle.png'.format(datahash, y), 'wb') as file:
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
        # w = w * (255 / w.max())
        # w = w.reshape((1, w.shape[0], 3))
        # img2 = Image.fromarray(w.astype(np.uint8))
        # img2.show()

        puzzle = Image.open(io.BytesIO(puzzle)).convert("RGBA")
        mask = (np.asarray(puzzle.getchannel("A")) / 255).mean(axis=0)
        puzzle = np.asarray(puzzle.convert("RGB")).sum(axis=0)

        bestx = 0
        leastdiff = 2147483647  # basically maxint, 999999 would work too but meh
        # difflist = []
        # TODO: move all of this crap to opencv matchTemplate because i'm basically remaking what was already done.
        for x in range(0, captcha.shape[0] - 30):
            diffarr = np.average(np.square(
                np.multiply(np.subtract(captcha[x:x + 30], puzzle, dtype="int64"), mask.reshape((mask.size, 1)))), 1)
            diff = np.mean(diffarr)
            # difflist.append(diff)
            if diff < leastdiff:
                bestx = x
                leastdiff = diff
            pass

        # asfd = np.array(difflist)
        # asfd = asfd - asfd.min()
        # asfd = asfd * (255 / asfd.max())
        # asfd = asfd.reshape((1, asfd.shape[0]))
        # img2 = Image.fromarray(asfd.astype(np.uint8))
        # img2 = img2.convert("RGB")
        # img2.putpixel((bestx, 0), (255, 0, 0))
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
