# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import json
from typing import AbstractSet, Any, Callable, Dict, List, Mapping, Optional, Tuple, Union, no_type_check
from pathlib import Path
from pydantic import BaseSettings, PrivateAttr
import pydantic.env_settings
import logging
import os
import logging
import ujson
import logging.handlers
from collections import OrderedDict

# try:
#     # Python 3.7 and newer, fast reentrant implementation
#     # witohut task tracking (not needed for that when logging)
#     from queue import SimpleQueue as Queue
# except ImportError:
#     from queue import Queue
# from typing import List

file_dir = os.path.split(os.path.realpath(__file__))[0]

logging.config.fileConfig(os.path.join("", 'logging.conf'), disable_existing_loggers=False)


def ozon_read_env_file(file_path: Path, *, encoding: str = None, case_sensitive: bool = False) -> Dict[
    str, Optional[str]]:
    try:
        from dotenv import dotenv_values
    except ImportError as e:
        raise ImportError('python-dotenv is not installed, run `pip install pydantic[dotenv]`') from e
    print("Read file")
    f_vars: Dict[str, Optional[str]] = dotenv_values(file_path, encoding=encoding or 'utf8')
    file_vars = {}
    for k, v in f_vars.items():
        if k in ["ADMINS", "PLUGINS", "DEPENDS"]:
            v = json.dumps([str(i) for i in v.split(",")])
        file_vars[k] = v
    print(file_vars)
    if not case_sensitive:
        return {k.lower(): v for k, v in file_vars.items()}
    else:
        return file_vars


pydantic.env_settings.read_env_file = ozon_read_env_file


class Settings(BaseSettings):
    module_name: str = "Awesome API"
    description: str = ""
    version: str = ""
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
    mongo_url: str = ""
    mongo_user: str = ""
    mongo_pass: str = ""
    mongo_db: str = ""
    app_code: str = ""
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
    admin_username = "admin"
    api_user_key = ""
    ldap_name: str = ""
    ldap_url: str = ""
    ldap_base_dn: str = ""
    ldap_bind_dn: str = ""
    plugins: List[str] = []
    depends: List[str] = []

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


# class SysConfig:
#     @classmethod
#     def get(cls):
#         with open('/app/config_system.json', mode="r") as jf:
#             data_j = jf.read()
#         return OrderedDict(ujson.loads(data_j))
