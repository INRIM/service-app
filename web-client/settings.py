# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from pydantic.tools import lru_cache
from fastapi.templating import Jinja2Templates
from config import *

templates = Jinja2Templates(directory="core/themes")


@lru_cache()
def get_settings():
    return SettingsApp()
