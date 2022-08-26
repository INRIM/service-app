# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from pydantic.tools import lru_cache
from fastapi.templating import Jinja2Templates
import config
import json
from pathlib import Path

templates = Jinja2Templates(
    directory=f"{Path(__file__).parent.absolute()}/core/themes")

# TODO test set Jinja2 work in async mode
# ,enable_async=True)


# setup Jinja2 filters

def cssid(input):
    """Custom filter"""
    return f"#{input}"


def cssid_div(input):
    """Custom filter"""
    return f"#{input}_div"


def parse_json(input):
    """Custom filter"""
    res = {}
    try:
        return json.loads(input)
    except Exception as e:
        return res


templates.env.filters['cssid'] = cssid
templates.env.filters['cssid_div'] = cssid_div
templates.env.filters['parse_json'] = parse_json


# eval settings and fill cache
@lru_cache()
def get_settings():
    return config.SettingsApp()
