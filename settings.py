from pydantic import BaseModel, computed_field, PrivateAttr
from pydantic_yaml import parse_yaml_file_as


class User(BaseModel):
    name: str
    cookies: dict
    user_agent: str
    proxy_pool: list[str] = []


class Settings(BaseModel):
    users: list[User]

    lolz_domain: str
    proxy_type: int

    found_count: int = 8

    low_time: int = 5
    high_time: int = 20
    switch_time: int = 1
    solve_time: int = 1

    anti_captcha_key: str
    site_key: str
    send_referral_to_creator: bool = True

    # TODO: this looks very hacky. find a better way
    _expire_blacklist = dict()

    @computed_field
    def lolz_url(self) -> str:
        return "https://" + self.lolz_domain + "/"


settings = parse_yaml_file_as(Settings, "settings.yaml")
