# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import logging

from fastapi import FastAPI, Request
from fastapi.responses import (
    JSONResponse,
)

from core.ContentService import ContentService
from core.Gateway import Gateway
from inrim.irq.CamundaRequisitionService import CamundaRequisitionService
from settings import get_settings, templates

logger = logging.getLogger(__name__)

requisition_api = FastAPI()


@requisition_api.post(
    "/start_requisition", tags=["requisition"]
)
async def start_requisition(
        request: Request
):
    params = request.query_params.__dict__["_dict"].copy()
    update_data = False
    if params.get("update_data"):
        update_data = True

    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    if update_data:
        content_service = await gateway.empty_content_service()
        data = submitted_data
    else:
        content = await gateway.get_record(submitted_data.get("data_model"))
        content["content"]["data"] = submitted_data.copy()

        content_service = ContentService.new(
            gateway=gateway, remote_data=content.copy()
        )
        stautus, data = await content_service.form_post_handler(submitted_data)
        if not stautus:
            return await content_service.form_post_complete_response(
                data, None
            )
    req_service = CamundaRequisitionService(
        content_service, "richiesta", data.get("name"),
    )
    response = await req_service.start(form_data=data, update_data=update_data)
    logger.info(f" Process start {req_service.process_instance_id}")
    return response


@requisition_api.post("/subscribe", tags=["requisition"])
async def subscribe(request: Request):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    content_service = await gateway.empty_content_service()
    process_service = ProcessService.new(content_service=content_service)
    response = await process_service.subscribe(
        form_data=submitted_data.get("process_id"))
    return response


@requisition_api.post("/cancel", tags=["requisition"])
async def cancell_process(request: Request):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    logger.info(submitted_data)
    content_service = await gateway.empty_content_service()
    process_service = ProcessService.new(content_service=content_service)
    response = await process_service.cancel(submitted_data.get("process_id"))
    return response


@requisition_api.post(
    "/complete", tags=["requisition"],
)
async def complete(
        request: Request
):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    content_service = await gateway.empty_content_service()
    process_service = CamundaRequisitionService(
        content_service=content_service,
        process_model="richiesta",
        process_name=submitted_data.get("req_name")
    )
    response = await process_service.complete(
        form_data=submitted_data, update_data=True
    )
    return response


@requisition_api.post("/reject", tags=["requisition"])
async def reject(request: Request):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    # logger.info(submitted_data)
    content_service = await gateway.empty_content_service()
    req_service = CamundaRequisitionService(
        content_service=content_service, process_model="richiesta",
        process_name=submitted_data.get("req_name")
    )
    response = await req_service.reject(form_data=submitted_data,
                                        update_data=True)
    return response


@requisition_api.post("/approve", tags=["requisition"])
async def approve(request: Request):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    # logger.info(submitted_data)
    content_service = await gateway.empty_content_service()
    req_service = CamundaRequisitionService(
        content_service=content_service, process_model="richiesta",
        process_name=submitted_data.get("req_name")
    )
    response = await req_service.approve(form_data=submitted_data,
                                         update_data=True)
    return response
