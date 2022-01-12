# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

import sys

sys.path.append("..")

from pydantic.tools import lru_cache
from config import *


@lru_cache()
def get_settings():
    return SettingsApp()

#
# def get_config_system():
#     return SysConfig.get()
