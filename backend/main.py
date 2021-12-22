# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

from ozon.api_base import *
# from inrim.auth import inrimAuth
import importlib


def fetch_dependecies(list_deps):
    for plugin in list_deps:
        try:
            logger.info(f"import module: {plugin}")
            module = importlib.import_module(plugin)
            deps = module.plugin_config.mod_config.get("depends", [])
            if deps:
                fetch_dependecies(deps)
        except ImportError as e:
            logger.error(f"Error import module: {plugin} msg: {e} ")


fetch_dependecies(get_settings().plugins)


# see init app for more info

@app.get("/", tags=["base"])
async def init(request: Request, ):
    resp = await request.scope['ozon'].home_page(request)
    return resp
