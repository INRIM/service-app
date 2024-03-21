# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import logging
import os
import string
import time
import uuid
from functools import lru_cache

from fastapi import FastAPI, Request, Header, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse

from models import *
import time as time_
from settings import *
import httpx

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

from core.Gateway import Gateway
from core.ContentService import ContentService
from core.AuthService import AuthContentService
from core.AttachmentService import AttachmentService
from core.MailService import MailService
from core.ImportService import ImportService
from core.SystemService import SystemService
from core.ClientMiddleware import ClientMiddleware
from core.OzonStaticFile import OzonStaticFile
from fastapi.staticfiles import StaticFiles
import ujson
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from core.cache.cache_utils import init_cache, stop_cache
from core.cache.cache import get_cache

from client_api import client_api
from auth_api import auth_api
from process_api import process_api
from requisition_api import requisition_api
import asyncio
import uvloop

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
        "content": {
            "application/json": {"example": {"detail": "Auth invalid"}}
        },
    },
    422: {
        "description": "Dati richiesta non corretti",
        "content": {
            "application/json": {"example": {"detail": "err messsage"}}
        },
    },
}
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
app = FastAPI(
    title=get_settings().module_name,
    description=get_settings().description,
    version=get_settings().version,
    openapi_tags=tags_metadata,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_event_handler("startup", init_cache)
app.add_event_handler("shutdown", stop_cache)

app.add_middleware(ClientMiddleware)

app.mount(
    "/static",
    StaticFiles(
        directory=f"{get_settings().basedir}/core/themes/{get_settings().theme}/static"
    ),
    name="static",
)
app.mount("/auth", auth_api)
app.mount("/client", client_api)
app.mount("/process", process_api)
app.mount("/requisition", requisition_api)


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
    list_data = request.headers.mutablecopy().__dict__["_list"]
    res = {
        item[0].decode("utf-8"): item[1].decode("utf-8") for item in list_data
    }
    return res.copy()


@app.get("/login/", tags=["base"])
async def login(
    request: Request,
):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    auth_service = ContentService.new(gateway=gateway, remote_data={})
    return await auth_service.get_login_page()


@app.get("/login", tags=["base"])
async def login(
    request: Request,
):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    auth_service = ContentService.new(gateway=gateway, remote_data={})
    return await auth_service.get_login_page()


@app.post("/login", tags=["base"])
async def login(
    request: Request,
):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    # auth_service = ContentService.new(gateway=gateway, remote_data={})
    return await gateway.server_post_action()


@app.post("/{path:path}")
async def proxy_post(request: Request, path: str):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    return await gateway.server_post_action()


@app.get("/{path:path}")
async def proxy_req(request: Request, path: str):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    return await gateway.server_get_action()


@app.delete("/{path:path}")
async def proxy_delete(request: Request, path: str):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    return await gateway.server_delete_action()


@app.on_event("startup")
async def startup_event():
    sys_service = SystemService.new(
        settings=get_settings(), templates=templates
    )
    await sys_service.check_and_init_service()
