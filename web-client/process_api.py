# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import ujson
from fastapi.responses import HTMLResponse, StreamingResponse, \
    RedirectResponse, JSONResponse
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


@process_api.post("/start/{process_model}/{process_name}",
                  tags=["process start instance"])
async def start_process(
        request: Request,
        process_model: str,
        process_name: str
):
    params = request.query_params.__dict__['_dict'].copy()
    update_data = False
    if params.get("update_data"):
        update_data = True

    gateway = Gateway.new(request=request, settings=get_settings(),
                          templates=templates)
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    if update_data:
        content_service = await gateway.empty_content_service()
        data = submitted_data
    else:
        content = await gateway.get_record(submitted_data.get('data_model'))
        content['content']['data'] = submitted_data.copy()

        content_service = ContentService.new(
            gateway=gateway, remote_data=content.copy())
        stautus, data = await content_service.form_post_handler(submitted_data)
        if not stautus:
            return await content_service.form_post_complete_response(data, None)
    process_service = ProcessService.new(
        content_service=content_service, process_model=process_model,
        process_name=process_name)
    await process_service.start(form_data=data, update_data=update_data)
    response = await process_service.check_process_status(
        process_service.process_instance_id)
    logger.info(f" Process start {process_service.process_instance_id}")
    return response


@process_api.post("/complete/{process_model}/{process_act_name}",
                  tags=["process complete task"])
async def complete_task(
        request: Request,
        process_model: str,
        process_act_name: str
):
    gateway = Gateway.new(request=request, settings=get_settings(),
                          templates=templates)
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    content_service = await gateway.empty_content_service()
    process_service = ProcessService.new(
        content_service=content_service, process_model=process_model,
        process_name=process_act_name)
    response = await process_service.complete(form_data=submitted_data,
                                              update_data=True)
    return response


@process_api.post("/cancel", tags=["process cancel instance"])
async def cancell_process(
        request: Request
):
    gateway = Gateway.new(request=request, settings=get_settings(),
                          templates=templates)
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
    gateway = Gateway.new(request=request, settings=get_settings(),
                          templates=templates)
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    logger.info(submitted_data)
    content_service = await gateway.empty_content_service()
    process_service = ProcessService.new(content_service=content_service)
    response = await process_service.next()
    return response
