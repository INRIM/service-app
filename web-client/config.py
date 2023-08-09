# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from typing import Optional, Dict, Any
import os
import pydantic
from pydantic import BaseSettings, PrivateAttr
from pathlib import Path
import json
import logging
import logging.config
import logging.handlers

# from aiologger import Logger

#
file_dir = Path(__file__).parent.absolute()

logging.config.fileConfig(
    Path(__file__).parent.joinpath("logging.conf"),
    disable_existing_loggers=False,
)


def json_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
    """
    A simple settings source that loads variables from a JSON file
    at the project's root.

    Here we happen to choose to use the `env_file_encoding` from Config
    when reading `config.json`
    """
    encoding = settings.__config__.env_file_encoding
    return json.loads(
        Path(__file__).parent.joinpath("config.json").read_text(encoding)
    )


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
    plugins: list = []
    depends: list = []
    admins: list = []
    demo: int = 0
    api_user_key: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_code = self.module_name

    class Config:
        env_file_encoding = "utf-8"
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
