# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

import sys
from pydantic.tools import lru_cache
import config


@lru_cache()
def get_settings():
    return config.SettingsApp()
