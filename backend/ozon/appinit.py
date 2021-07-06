# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import sys
import logging
import os
import string
import time
import uuid
import requests
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
from .core.Ozon import Ozon
from .core.OzonRawMiddleware import OzonRawMiddleware
from collections import OrderedDict

# Inrim Vericalizations
# from .inrim.auth.OzonInrimAuth import OzonInrimAuth, InrimSessionService

# TODO project specific

logger = logging.getLogger(__name__)

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
    title=get_settings().app_name,
    description=get_settings().app_desc,
    version="1.0.0",
    openapi_tags=tags_metadata,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)


app.add_middleware(
    OzonRawMiddleware, ozon_class=Ozon
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
    logger.info(f"rid={idem} START request path={request.url.path}, req_id={request.headers.get('req_id')}")
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
async def get_my_session(request: Request):
    sess = request.scope['ozon'].session
    sess.app['save_session'] = False
    sess.server_settings = {}
    return sess


@app.get("/allowed_user/{uid}", tags=["base"])
async def allowed_user(uid: str):
    return await list_allowed_users(uid)


@app.get("/check_and_init_db", tags=["base"])
async def default_layout(request: Request):
    session = request.scope['ozon'].session
    await request.scope['ozon'].check_and_init_db()
    return {"status": "Done"}


# TODO spostare login logout quando possibile

@app.get("/login", tags=["base"])
async def login(
        request: Request,
        token: Optional[str] = "",
):
    # settings = get_settings()
    logger.info("LOOOOOGIN")
    logger.info(" --> Login ")
    base_url_ref = request.headers.get("base_url_ref")
    if not base_url_ref:
        ref = f'http://{request.headers.get("host")}/action/list_form'
    else:
        ref = f'{base_url_ref}/action/list_form'
    resp = JSONResponse({
        "action": "redirect",
        "url": f"{ref}",
    })
    resp.set_cookie('authtoken', value=token)
    resp.headers['apitoken'] = token
    return resp


@app.get("/logout", tags=["base"])
async def logout(
        request: Request,
):
    # settings = get_settings()
    resp = await request.scope['ozon'].logout_response(request)
    # await InrimAuth(get_settings().authentication_key, get_settings().authentication_url).logout(token)
    return resp
