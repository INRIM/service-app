# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

from ozon.api_base import *
# from inrim.auth import inrimAuth

for plugin in get_settings().plugins:
    try:
        importlib.import_module(plugin)
    except ImportError as e:
        logger.error(f"Error import module: {module} msg: {e} ")

# see init app for more info

@app.get("/", tags=["base"])
async def init(request: Request, ):
    resp = await request.scope['ozon'].home_page(request)
    return resp
