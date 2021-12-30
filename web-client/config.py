# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from typing import Optional
import os
from pydantic import BaseSettings, PrivateAttr
from pathlib import Path
import json
import logging
import logging.handlers

# from aiologger import Logger

#
file_dir = os.path.split(os.path.realpath(__file__))[0]
#
logging.config.fileConfig(os.path.join(file_dir, 'logging.conf'), disable_existing_loggers=False)


# try:
#     # Python 3.7 and newer, fast reentrant implementation
#     # witohut task tracking (not needed for that when logging)
#     from queue import SimpleQueue as Queue
# except ImportError:
#     from queue import Queue
# from typing import List

# logger = logging.getLogger(__name__)
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
#     Replace handlers on the logger logger with a LocalQueueHandler,
#     and start a logging.QueueListener holding the original
#     handlers.
#
#     """
#     print("set up logging")
#     queue = Queue()
#     handler = LocalQueueHandler(queue)
#     c_hdl = logging.StreamHandler()
#     formatter = logging.Formatter(
#         '[%(asctime)s | %(levelname)-6s | %(filename)s:%(lineno)s - %(funcName)s]: %(message)s')
#
#     logger.setLevel(logging.INFO)
#     handler.setLevel(logging.INFO)
#
#     logger.addHandler(handler)
#     c_hdl.setFormatter(formatter)
#     listener = logging.handlers.QueueListener(queue, c_hdl)
#     listener.start()
#
#
# setup_logging_queue()

# def json_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
#     """
#     A simple settings source that loads variables from a JSON file
#     at the project's root.
#
#     Here we happen to choose to use the `env_file_encoding` from Config
#     when reading `config.json`
#     """
#     encoding = settings.__config__.env_file_encoding
#     return json.loads(Path('config.json').read_text(encoding))


class SettingsApp(BaseSettings):
    module_name: str = "Awesome API"
    module_label: str = "Awesome API"
    description: str = ""
    version: str = "0.0.0"
    app_code: str = ""
    service_url: str = "http://backend:8225"
    base_url: str = ""
    server_datetime_mask: str = ""
    server_date_mask = ""
    ui_datetime_mask: str = ""
    ui_date_mask = ""
    tz: str = ""
    logo_img_url: str = ""
    stack: str = ""
    builder_component_url: str = False
    basedir = file_dir
    theme: str = "italia"
    report_footer_company: str = ""
    report_footer_title: str = ""
    report_footer_sub_title: str = ""
    report_footer_pagination: int = 0
    report_header_space: str = ""
    report_footer_space: str = ""
    upload_folder = ""
    plugins = []
    admins = []
    demo: int = 0

    class Config:
        env_file = ".env"
