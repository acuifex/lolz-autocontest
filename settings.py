import json

# TODO: Doing settings this way is probably dumb. Find another way

f = open('settings.json')
data = json.load(f)
imagesDir = "ErrorImages/"
users = data["users"]
lolzdomain = data["lolz_domain"]
answers_server = data["answers_server"]
try_questions = data["try_questions"]
lolzUrl = "https://" + lolzdomain + "/"
proxy_type = data["proxy_type"]
found_count = data["found_count"]
low_time = data["low_time"]
high_time = data["high_time"]
switch_time = data["switch_time"]
solve_time = data["solve_time"]
f.close()

# TODO: this looks very hacky. find a better way
ExpireBlacklist = dict()