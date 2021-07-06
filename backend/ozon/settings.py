# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.

import sys
sys.path.append("..")

from pydantic.tools import lru_cache
import config


@lru_cache()
def get_settings():
    return config.SettingsApp()
