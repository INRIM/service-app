# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from pydantic.tools import lru_cache
from fastapi.templating import Jinja2Templates
import config

templates = Jinja2Templates(directory="core/themes")

# setup Jinja2 filters

def cssid(input):
    """Custom filter"""
    return f"#{input}"

def cssid_div(input):
    """Custom filter"""
    return f"#{input}_div"

templates.env.filters['cssid'] = cssid
templates.env.filters['cssid_div'] = cssid_div

# eval settings and fill cache
@lru_cache()
def get_settings():
    return config.SettingsApp()
