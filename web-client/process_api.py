# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import ujson
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, JSONResponse
from typing import Optional
from fastapi import FastAPI, Request, Header, HTTPException, Depends, Response
from core.Gateway import Gateway
from core.ContentService import ContentService
from core.ProcessService import ProcessService
from settings import get_settings, templates
import logging
from io import BytesIO
import aiofiles

logger = logging.getLogger(__name__)

process_api = FastAPI()


@process_api.post("/start/{process_model}/{process_name}", tags=["process start instance"])
async def start_process(
        request: Request,
        process_model: str,
        process_name: str
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    content_service = await gateway.empty_content_service()
    process_service = ProcessService.new(
        content_service=content_service, process_model=process_model, process_name=process_name)
    await process_service.start(form_data=submitted_data)
    response = await process_service.check_process_status(process_service.process_instance_id)
    logger.info(f" Process start {process_service.process_instance_id}")
    return response


@process_api.post("/complete", tags=["process complete task"])
async def complete_task(
        request: Request
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    content_service = await gateway.empty_content_service()
    process_service = ProcessService.new(
        content_service=content_service, process_model=process_model, process_name=process_name)
    response = await process_service.complete(form_data=submitted_data)
    return response


@process_api.post("/cancel", tags=["process cancel instance"])
async def cancell_process(
        request: Request
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    logger.info(submitted_data)
    content_service = await gateway.empty_content_service()
    process_service = ProcessService.new(content_service=content_service)
    response = await process_service.cancel()
    return response


@process_api.post("/next", tags=["process next task"])
async def modal_action(
        request: Request
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    logger.info(submitted_data)
    content_service = await gateway.empty_content_service()
    process_service = ProcessService.new(content_service=content_service)
    response = await process_service.next()
    return response
