# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.

from ozon.api_base import *
from inrim.auth import inrimAuth


# see init app for more info

@app.get("/", tags=["base"])
async def init(request: Request, ):
    resp = await request.scope['ozon'].home_page(request)
    return resp
