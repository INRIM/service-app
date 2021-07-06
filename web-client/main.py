# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import logging
import os
import string
import time
import uuid
from functools import lru_cache
import requests

from fastapi import FastAPI, Request, Header, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse

from models import *
import time as time_
from settings import get_settings, templates
import httpx

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

from core.Gateway import Gateway

import ujson
from fastapi.templating import Jinja2Templates

from client_api import client_api
from inrim.ThemeConfigInrim import ThemeConfigInrim

logger = logging.getLogger(__name__)

tags_metadata = [
    {
        "name": ":-)",
        "description": "Forms Inrim",
    },
    {
        "name": "base",
        "description": "API Base",
    },
]

responses = {
    401: {
        "description": "Token non valido",
        "content": {"application/json": {"example": {"detail": "Auth invalid"}}}},
    422: {
        "description": "Dati richiesta non corretti",
        "content": {"application/json": {"example": {"detail": "err messsage"}}}}
}

app = FastAPI(
    title=get_settings().app_name,
    description=get_settings().app_desc,
    version="1.0.0",
    openapi_tags=tags_metadata,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.mount("/static", StaticFiles(directory=f"core/themes/{get_settings().theme}/static"), name="static")
app.mount("/client", client_api)


# app.mount("/design", builder_api)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    idem = str(uuid.uuid4())
    logger.info(f"rid={idem} start request path={request.url.path}, req_id={request.headers.get('req_id')}")
    start_time = time_.time()

    response = await call_next(request)

    process_time = (time_.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    logger.info(
        f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}, "
        f"req_id={response.headers.get('req_id')}"
    )
    # print(request.headers)
    if response.status_code == 404:
        return RedirectResponse("/")
    return response


@app.get("/status", tags=["base"])
async def service_status():
    """
    Ritorna lo stato del servizio
    """
    return {"status": "live"}


@app.get("/favicon.ico", tags=["base"])
async def favicon():
    """
    Ritorna lo stato del servizio
    """
    RedirectResponse("/static/favicon/favicon.ico")



def deserialize_header_list(request):
    list_data = request.headers.mutablecopy().__dict__['_list']
    res = {item[0].decode("utf-8"): item[1].decode("utf-8") for item in list_data}
    return res.copy()


@app.post("/{path:path}")
async def proxy_post(request: Request, path: str):
    gateway = await Gateway.create(request, get_settings(), templates)
    return await gateway.server_post_action()


@app.get("/{path:path}")
async def proxy_req(request: Request, path: str):
    gateway = await Gateway.create(request, get_settings(), templates)
    return await gateway.server_get_action()

@app.delete("/{path:path}")
async def proxy_delete(request: Request, path: str):
    gateway = await Gateway.create(request, get_settings(), templates)
    return await gateway.server_delete_action()
