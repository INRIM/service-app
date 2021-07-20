# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
from typing import Optional

from pydantic import BaseSettings, PrivateAttr
import logging
import os

file_dir = os.path.split(os.path.realpath(__file__))[0]

logging.config.fileConfig(os.path.join(file_dir, 'logging.conf'), disable_existing_loggers=False)


class Settings(BaseSettings):
    app_name: str = "Awesome API"
    app_desc: str = ""
    app_version: str = ""
    service_url: str = ""

    class Config:
        env_file = ".env"


class SettingsApp(Settings):
    server_datetime_mask: str = ""
    server_date_mask = ""
    ui_datetime_mask: str = ""
    ui_date_mask = ""
    tz: str = ""
    logo_img_url: str = ""
    builder_component_url: str = False
    theme: str = "italia"
    report_footer_company: str = ""
    report_footer_title: str = ""
    report_footer_sub_title: str = ""
    report_footer_pagination: int = 0
    report_header_space: str = ""
    report_footer_space: str = ""
