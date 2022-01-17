# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

import sys
from pydantic.tools import lru_cache
from config import *


@lru_cache()
def get_settings():
    return SettingsApp()
