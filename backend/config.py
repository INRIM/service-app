# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

from typing import Optional, List, Dict

from pydantic import BaseSettings, PrivateAttr
import logging
import logging.config
import os

file_dir = os.path.split(os.path.realpath(__file__))[0]

logging.config.fileConfig(os.path.join("", 'logging.conf'), disable_existing_loggers=False)

class Settings(BaseSettings):
    app_name: str = "Awesome API"
    app_desc: str = ""
    app_version: str = ""
    base_key: str = ""
    base_url_ws: str = ""
    camunda_url: str = ""
    app_process: str = ""
    jwt_secret: str = ""
    jwt_alg: str = "HS256"
    jwt_expire_minute: Optional[int] = None
    _jwt_settings: dict = PrivateAttr()
    default_dn: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._jwt_settings = {
            "secret": self.jwt_secret,
            "alg": self.jwt_alg,
            "expire_minute": self.jwt_expire_minute,
        }

    class Config:
        env_file = ".env"


class SettingsApp(Settings):
    people_headerkey: str = ""
    people_url: str = ""
    people_key: str = ""
    authentication_headerkey: str = ""
    authentication_url: str = ""
    authentication_key: str = ""
    ui_builder_url: str = ""
    ui_builder_key: str = ""
    data_builder_url: str = ""
    data_builder_key: str = ""
    data_builder_headerkey: str = ""
    mongo_url: str = ""
    mongo_user: str = ""
    mongo_pass: str = ""
    mongo_db: str = ""
    mongo_replica: str = ""
    server_datetime_mask: str = ""
    server_date_mask = ""
    ui_datetime_mask: str = ""
    ui_date_mask = ""
    tz: str = ""
    logo_img_url: str = ""
    use_auth: int = 1
    demo: int = 0
    admins: List[str] = []
    internal: Dict = {}
    delete_record_after_days = 2
    refresh_setting_hours = 24
    session_expire_hours = 12
    upload_folder = ""
    base_admin_username = "admin"
    ldap_name: str = ""
    ldap_url: str = ""
    ldap_base_dn: str = ""
    ldap_bind_dn: str = ""
    plugins = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.mongo_replica == "":
            self.mongo_replica = None

    def get_sevice_dict(self, service_name):
        res = {}
        data = self.dict()
        for item in self.dict():
            if service_name in item:
                key = item.split("_")[1]
                res[key] = data[item]
        return res

    def get_by_name(self, name):
        data = self.dict()
        return data.get(name, "")
