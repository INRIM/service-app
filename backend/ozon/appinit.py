# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
import logging
import os
import string
import time
import uuid
import requests
import ujson
import time as time_
from fastapi import FastAPI
from .settings import *
from starlette.middleware import Middleware
from fastapi import Request, Header, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse, UJSONResponse
from typing import List, Optional, Dict, Any, Literal, Union
from starlette.middleware import Middleware

# from .services.services import *
from .core.database.mongodb.mongodb_utils import close_mongo_connection, connect_to_mongo
from .core.Ozon import Ozon
from .core.OzonRawMiddleware import OzonRawMiddleware
from .core.ServiceMain import ServiceMain
from collections import OrderedDict
from passlib.context import CryptContext
import importlib
import aiofiles

# TODO project specific
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

with open('/app/config_system.json', mode="rb") as jf:
    data_j = jf.read()

config_system = ujson.loads(data_j)

tags_metadata = [
    {
        "name": ":-)",
        "description": 'Forms Inrim: <a href="/resources/docs">Resouces Docs</a> and <a href="/builder/docs">Builder Docs </a>',
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
    title=get_settings().module_name,
    description=get_settings().description,
    version="1.0.0",
    openapi_tags=tags_metadata,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)

app.add_middleware(
    OzonRawMiddleware, pwd_context=pwd_context
)

component_types = [
    OrderedDict({"id": "project", "title": "Project"}),
    OrderedDict({"id": "layout", "title": "Layout"}),
    OrderedDict({"id": "form", "title": "Form"}),
    OrderedDict({"id": "resource", "title": "Resource"})
]


def check_response_data(res_data: dict) -> dict:
    if res_data.get("status") and res_data.get("status") == "error":
        raise HTTPException(status_code=422, detail=res_data['message'])
    else:
        return res_data


@app.middleware("http")
async def log_requests(request: Request, call_next):
    idem = str(uuid.uuid4())
    app_code = request.headers.get('app_code')
    logger.info(
        f"rid={idem} START request path={request.url.path}, req_id={request.headers.get('req_id')}, app_code:{app_code}")
    start_time = time_.time()

    response = await call_next(request)

    process_time = (time_.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    logger.info(
        f"END rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code},"
        f"req_id={response.headers.get('req_id')}"
    )
    if response.status_code == 404:
        response = JSONResponse({
            "action": "redirect",
            "url": f"/",
        })

    return response


@app.get("/status", tags=["base"])
async def service_status():
    """
    Ritorna lo stato del servizio
    """
    return {"status": "live"}


@app.get("/session", tags=["base"])
async def get_my_session(
        request: Request,
        apitoken: str = Header(None),
        app_code: str = Header(None)
):
    sess = request.scope['ozon'].session
    # sess.app['save_session'] = False
    sess.server_settings = {}
    return sess.get_dict().copy()


# TODO remove
# @app.get("/check_and_init_db", tags=["base"])
# async def default_layout(
#         request: Request,
#         apitoken: str = Header(None)
# ):
#     session = request.scope['ozon'].session
#     # await request.scope['ozon'].check_and_init_db()
#     return {"status": "Done"}


@app.get("/login", tags=["base"])
async def login(
        request: Request,
        app_code: str = Header(None)

):
    # settings = get_settings()
    logger.info(" --> Login ")
    service = ServiceMain.new(request=request)
    schema = await service.service_get_schema("login")
    return {
        "editable": True,
        "model": "login",
        "action_url": "/login",
        "action_name": "",
        "context_buttons": [],
        "schema": schema,
        "data": {},
    }


@app.post("/login", tags=["base"])
async def login(
        request: Request,
        token: Optional[str] = "",
        app_code: str = Header(None)
):
    # settings = get_settings()
    logger.info(" User --> Login ")
    auth_service = request.scope['ozon'].auth_service
    return await auth_service.login()


@app.get("/logout", tags=["base"])
async def logout(
        request: Request,
        apitoken: str = Header(None),
        app_code: str = Header(None)
):
    # settings = get_settings()
    auth_service = request.scope['ozon'].auth_service
    resp = await auth_service.logout()
    return resp


@app.on_event("startup")
async def startup_event():
    ozon = Ozon.new(pwd_context=pwd_context)
    await ozon.compute_check_and_init_db(config_system.copy())
    await ozon.check_and_init_db()
