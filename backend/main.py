# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

from api_base import *
import logging
import ujson
import sys
import pathlib

logger = logging.getLogger(__name__)

import importlib

sys.path.append(pathlib.Path(__file__).parent.resolve())


def fetch_dependecies(list_deps):
    for plugin in list_deps:
        try:
            logger.info(f"import py module: {plugin}")
            sys.path.append(plugin)
            importlib.import_module(plugin)
        except ImportError as e:
            logger.error(f"Error import module: {plugin} msg: {e} ")


fetch_dependecies(get_settings().depends)


# see init app for more info


@app.get("/", tags=["base"])
async def init(
    request: Request,
):
    resp = await request.scope["ozon"].home_page(request)
    return resp
