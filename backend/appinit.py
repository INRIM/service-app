# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
import logging
import os
import string
import uuid
import requests
import ujson
import time as time_
from fastapi import FastAPI
from settings import *
from starlette.middleware import Middleware
from fastapi import Request, Header, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse, UJSONResponse
from typing import List, Optional, Dict, Any, Literal, Union
from starlette.middleware import Middleware

from ozon.core.database.mongodb.mongodb_utils import close_mongo_connection, \
    connect_to_mongo
from ozon.core.database.cache.cache_utils import init_cache, stop_cache
from ozon.core.Ozon import Ozon
from ozon.core.OzonRawMiddleware import OzonRawMiddleware
from fastapi.middleware.cors import CORSMiddleware
from ozon.core.ServiceMain import ServiceMain
from collections import OrderedDict
from passlib.context import CryptContext
import importlib
import aiofiles

# TODO project specific
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

tags_metadata = [
    {
        "name": ":-)",
        "description": 'Forms Inrim: <a href="/resources/docs">'
                       'Resouces Docs</a> and <a href="/builder/docs"'
                       '>Builder Docs </a>',
    },
]

responses = {
    401: {
        "description": "Token non valido",
        "content": {
            "application/json": {"example": {"detail": "Auth invalid"}}}},
    422: {
        "description": "Dati richiesta non corretti",
        "content": {
            "application/json": {"example": {"detail": "err messsage"}}}}
}

# angular testing
# origins = [
#     "http://localhost:4200",
#     "http://localhost:8080",
# ]

app = FastAPI(
    title=get_settings().module_name,
    description=get_settings().description,
    version=get_settings().version,
    openapi_tags=tags_metadata,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("startup", init_cache)

app.add_event_handler("shutdown", close_mongo_connection)
app.add_event_handler("shutdown", stop_cache)

app.add_middleware(
    OzonRawMiddleware, pwd_context=pwd_context, settings=get_settings()
)
# angular testing
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

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
        f"END rid={idem} completed_in={formatted_process_time} ms status_code={response.status_code},"
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
    sess.server_settings = {}
    return sess.get_dict().copy()


@app.post("/builder_mode/{mode}", tags=["base"])
async def builder_mode(
        request: Request,
        mode: int,
        apitoken: str = Header(None),
):
    logger.info("setup buider_mode")
    app_code = request.scope['ozon'].session.app.get('app_code', "")
    request.scope['ozon'].session.apps[app_code]['builder'] = mode > 0
    request.scope['ozon'].session.app['builder'] = mode > 0
    request.scope['ozon'].session.app['save_session'] = True
    auth_service = request.scope['ozon'].auth_service
    logger.info("end setup buider_mode")
    return auth_service.reload_page_response()


@app.get("/login", tags=["base"])
async def login(
        request: Request,
        app_code: str = Header(None)

):
    logger.info(" --> Login ")
    service = ServiceMain.new(request=request, settings=get_settings())
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
    logger.info(" User --> Login ")
    auth_service = request.scope['ozon'].auth_service
    return await auth_service.login()


@app.get("/logout", tags=["base"])
async def logout(
        request: Request,
        apitoken: str = Header(None),
        app_code: str = Header(None)
):
    auth_service = request.scope['ozon'].auth_service
    resp = await auth_service.logout()
    return resp


@app.on_event("startup")
async def startup_event():
    ozon = Ozon.new(pwd_context=pwd_context, settings=get_settings())
    if get_settings().init_db:
        await ozon.init_apps(get_settings().dict())
