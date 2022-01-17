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


def json_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
    """
    A simple settings source that loads variables from a JSON file
    at the project's root.

    Here we happen to choose to use the `env_file_encoding` from Config
    when reading `config.json`
    """
    encoding = settings.__config__.env_file_encoding
    return json.loads(Path('config.json').read_text(encoding))


class SettingsBase(BaseSettings):
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

    class Config:
        env_file_encoding = 'utf-8'
        extra = pydantic.Extra.ignore

        @classmethod
        def customise_sources(
                cls,
                init_settings,
                env_settings,
                file_secret_settings,
        ):
            return (
                init_settings,
                json_config_settings_source,
                env_settings,
                file_secret_settings,
            )


class SettingsApp(SettingsBase):
    module_group: str = ""
    mongo_url: str = ""
    mongo_user: str = ""
    module_type: str = ""
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
    admins: List[str] = []
    depends: List[str] = []
    init_db: bool = True
    builder_mode: bool = False

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_code = self.module_name
        self._jwt_settings = {
            "secret": self.jwt_secret,
            "alg": self.jwt_alg,
            "expire_minute": self.jwt_expire_minute,
        }
