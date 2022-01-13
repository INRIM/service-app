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
    api_user_key: str = ""

    class Config:
        env_file = ".env"
