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
import json
from noise import pnoise1
import vectormath as vmath

import settings

pattern_captcha_sid = re.compile(r"sid\s*:\s*'([0-9a-f]{32})'", re.MULTILINE)
pattern_captcha_dot = re.compile(r'XenForo.ClickCaptcha.dotSize\s*=\s*(\d+);', re.MULTILINE)
pattern_captcha_img = re.compile(r'XenForo.ClickCaptcha.imgData\s*=\s*"([A-Za-z0-9+/=]+)";', re.MULTILINE)
pattern_hint_letter = re.compile(r'Starts with \'(.)\' letter', re.MULTILINE)


class SolverAnswers:
    def __init__(self, puser):
        self.puser = puser

    def solve(self, captchaBlockSoup, **kwargs) -> Union[dict, None]:
        question = captchaBlockSoup.find("div", attrs={"class": "ddText"}).text
        placeholder = captchaBlockSoup.find("input", attrs={"id": "CaptchaQuestionAnswer"})["placeholder"]

        # TODO: add exact threadid search
        params = {
            "id": kwargs["id"],
            "q": question,
        }

        if placeholder:
            params["l"] = pattern_hint_letter.search(placeholder).group(1)

        response = self.puser.makerequest("GET", "https://" + settings.answers_server + "/query.php", params=params,
                                          timeout_eventlet=15, timeout=12.05, retries=3, checkforjs=False)

        if response is None:
            return None

        resp = response.json()

        if resp["status"] < 0:
            self.puser.logger.warning("%d doesn't have an answer. blacklisting for 5 minutes", kwargs["id"])
            settings.ExpireBlacklist[kwargs["id"]] = time.time() + 300 # TODO: make configurable timeout
            return None
        if resp["status"] > 0: # TODO: make this check configurable
            self.puser.logger.warning("%d %d answer isn't exact. blacklisting for 5 minutes", resp["threadid"], resp["id"])
            settings.ExpireBlacklist[kwargs["id"]] = time.time() + 300
            return None
        self.puser.logger.verbose("using %d %d %d", resp["threadid"], resp["id"], resp["status"])

        time.sleep(settings.solve_time)
        return {
            'captcha_question_answer': resp["answer"],
            'captcha_type': "AnswerCaptcha",
        }

class SolverSlider2:
    def __init__(self, puser):
        self.puser = puser

    # makes curved line with perlin noise. doesn't include the end position
    # TODO: maybe move this out of the class definition?
    def makeline(self,
                 start_pos: vmath.Vector2,
                 end_pos: vmath.Vector2,
                 move_time_ms: int,
                 amplitude,
                 time_offset_ms: int) -> list:
        out_arr = []
        # // is int division aka division for normal people
        step_count = move_time_ms // 15
        dir = end_pos - start_pos
        # vmath.Vector2 is used to make a copy. normalize modifies the instance
        dir_norm = vmath.Vector2(dir).normalize()
        # vector rotated by 90 degrees
        dir_norm_rot = vmath.Vector2(dir_norm.y, -dir_norm.x)
        step_length = dir.length / step_count
        # a hack to make "random" paths.
        perlin_base = random.randint(0, 1000)

        for i in range(step_count):
            pos = start_pos + dir_norm * step_length * i
            noise = pnoise1(i / step_count, 2, lacunarity=2.5, persistence=0.2, base=perlin_base)
            # apply noise sideways to the path
            pos += dir_norm_rot * noise * amplitude
            # +- 2 ms for slight realism, lolz also has that
            out_arr.append([0x02, pos, time_offset_ms + i * 15 + random.randint(-2, 2)])

        return out_arr

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

        # approximate positions of different points of interest
        start_pos = vmath.Vector2(random.randint(int(0.25 * self.puser.monitor_dims[0]), int(0.75 * self.puser.monitor_dims[0])),
                                  random.randint(int(0.05 * self.puser.monitor_dims[1]), int(0.45 * self.puser.monitor_dims[1])))
        captcha_pos = vmath.Vector2(random.randint(int(0.1 * self.puser.monitor_dims[0]), int(0.2 * self.puser.monitor_dims[0])),
                                    random.randint(int(0.4 * self.puser.monitor_dims[1]), int(0.75 * self.puser.monitor_dims[1])))
        # + 0.01 is needed so we don't make the end pos in the exact same spot.
        # you can't normalize a vector of length 0
        end_pos = vmath.Vector2(captcha_pos.x + x + 0.01,
                                captcha_pos.y + random.randint(-5, 5))
        monitor_length = vmath.Vector2(self.puser.monitor_dims[0], self.puser.monitor_dims[1]).length

        # 0.075 and 0.0375 are chosen arbitrarily. maybe scale them with path length too?
        start_captcha_path = self.makeline(start_pos,
                                           captcha_pos,
                                           random.randint(500, 1000),
                                           0.075 * monitor_length,
                                           current_time_ms)
        captha_end_path = self.makeline(captcha_pos,
                                        end_pos,
                                        random.randint(500, 1000),
                                        0.0375 * monitor_length,
                                        start_captcha_path[-1][2] + random.randint(100, 200))
        captha_end_path[0][0] = 0x00
        slider_path = start_captcha_path + captha_end_path + [[0x01, end_pos, captha_end_path[-1][2] + random.randint(100, 500)]]

        tmp = b""
        for i in slider_path:
            tmp += struct.pack("<BiiQ", i[0],
                               int(i[1].x),
                               int(i[1].y),
                               i[2])

        encrypted = self.applyencryption(datahash & 0xffff, tmp)

        requestdata = b"hack_me_if_you_can\n" + sid + encrypted
        response = self.puser.makerequest("POST", "https://captcha." + settings.lolzdomain + "/captcha",
                                          headers={'referer': "https://lolz.guru/",
                                                   'origin': "https://lolz.guru"}, cookies={}, data=requestdata,
                                          timeout_eventlet=15, timeout=12.05, retries=3, checkforjs=False)

        if response is None:
            return None

        return int.from_bytes(response.content, byteorder='little')

    def solve(self, captchaBlockSoup, **kwargs) -> Union[dict, None]:
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
            raise RuntimeError("y value from captcha response is invalid: {}".format(y))

        x, diff = self.findPuzzlePosition(captcha, puzzle, y)
        self.puser.logger.debug("solved x,y: %d,%d diff: %.2f", x, y, diff)

        time.sleep(settings.solve_time)

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

    def solve(self, captchaBlockSoup, **kwargs) -> Union[dict, None]:
        captchahash = captchaBlockSoup.find("input", attrs={"name": "captcha_hash"}).get("value")
        scriptcaptcha = captchaBlockSoup.find("script")
        dot = int(pattern_captcha_dot.search(scriptcaptcha.string).group(1))
        if dot != 20:
            raise RuntimeError("dotsize isn't 20 but instead is {}".format(dot))

        img = pattern_captcha_img.search(scriptcaptcha.string).group(1)
        x, y, confidence = self.findCirclePosition(img)
        if confidence < 180.0:
            self.puser.logger.verbose("confidence is pretty bad (%.2f < 180.0). let's try again later", confidence)
            return None

        self.puser.logger.debug("solved x,y: %d,%d confidence: %.2f", x, y, confidence)
        time.sleep(settings.solve_time)
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
