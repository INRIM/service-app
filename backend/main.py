# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

from ozon.api_base import *
# from inrim.admin import inrimAuth
import logging
import ujson
logger = logging.getLogger(__name__)

import importlib


def fetch_dependecies(list_deps):
    for plugin in list_deps:
        try:
            logger.info(f"import module: {plugin}")
            importlib.import_module(plugin)
        except ImportError as e:
            logger.error(f"Error import module: {plugin} msg: {e} ")


fetch_dependecies(config_system['depends'])


# see init app for more info

@app.get("/", tags=["base"])
async def init(request: Request, ):
    resp = await request.scope['ozon'].home_page(request)
    return resp
