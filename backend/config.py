# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

from typing import Optional, List, Dict

from pydantic import BaseSettings, PrivateAttr
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


# root = logging.getLogger()
#
#
# # https://www.zopatista.com/python/2019/05/11/asyncio-logging/
# class LocalQueueHandler(logging.handlers.QueueHandler):
#     def emit(self, record: logging.LogRecord) -> None:
#         # Removed the call to self.prepare(), handle task cancellation
#         try:
#             self.enqueue(record)
#         except asyncio.CancelledError:
#             raise
#         except Exception:
#             self.handleError(record)
#
#
# def setup_logging_queue() -> None:
#     """Move log handlers to a separate thread.
#
#     Replace handlers on the root logger with a LocalQueueHandler,
#     and start a logging.QueueListener holding the original
#     handlers.
#
#     """
#
#     queue = Queue()
#     handler = LocalQueueHandler(queue)
#     c_hdl = logging.StreamHandler()
#     formatter = logging.Formatter(
#         '[%(asctime)s | %(levelname)-6s | %(filename)s:%(lineno)s - %(funcName)s]: %(message)s')
#
#     root.setLevel(logging.INFO)
#     handler.setLevel(logging.INFO)
#
#     root.addHandler(handler)
#     c_hdl.setFormatter(formatter)
#     listener = logging.handlers.QueueListener(queue, c_hdl)
#     listener.start()
#
# setup_logging_queue()


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


class SysConfig:
    @classmethod
    def get(cls):
        with open('/app/config_system.json', mode="r") as jf:
            data_j = jf.read()
        return OrderedDict(ujson.loads(data_j))
