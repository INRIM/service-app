# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.

from ozon.api_base import *
from inrim.auth import inrimAuth


# see init app for more info

@app.get("/", tags=["base"])
async def init(
        request: Request, ):
    session = request.scope['ozon'].session
    # await check_and_init_db(session)

    session.app['mode'] = "list"
    session.app['component'] = "form"

    return JSONResponse({
        "action": "redirect",
        "url": "/action/list_form",
    })
