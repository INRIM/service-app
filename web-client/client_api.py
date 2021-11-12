# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import ujson
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, JSONResponse
from typing import Optional
from fastapi import FastAPI, Request, Header, HTTPException, Depends, Response
from core.Gateway import Gateway
from core.ContentService import ContentService
from core.ExportService import ExportService
from settings import get_settings, templates
import logging
from io import BytesIO
import aiofiles

logger = logging.getLogger(__name__)

client_api = FastAPI()


@client_api.post("/fast_search", tags=["client"])
async def modal_action(
        request: Request
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    logger.info(submitted_data)
    field = submitted_data['field']
    content_service = await gateway.content_service_from_record(submitted_data['fast_serch_model'], rec_name="")
    response = await content_service.fast_search_eval(submitted_data['data'].copy(), field)
    return response


@client_api.post("/modal/action", tags=["client"])
async def modal_action(
        request: Request
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    submitted_data = await gateway.load_post_request_data()
    # if not dict is error
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    if submitted_data.get('url'):
        action_url = submitted_data.get('url')
    else:
        action_url = f"/action/{submitted_data.get('action')}/{submitted_data.get('record')}"
    response = await gateway.server_get_action(url_action=action_url, modal=True)
    return response


@client_api.get("/grid/{key}/{model}/rows/", tags=["client"])
async def client_grid_rows(
        request: Request, key: str, model: str
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    res = await gateway.compute_datagrid_rows(key, model, rec_name="")
    return res


@client_api.get("/grid/{key}/{model}/rows/{rec_name}", tags=["client"])
async def client_grid_rows_data(
        request: Request, key: str, model: str, rec_name: str
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    res = await gateway.compute_datagrid_rows(key, model, rec_name=rec_name)
    return res


@client_api.post("/grid/{key}/{model}/{num_rows}/newrow", tags=["client"])
async def client_grid_new_row(
        request: Request, key: str, model: str, num_rows: int,
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    res = await gateway.compute_datagrid_add_row(key, num_rows, model, rec_name="")
    return res


@client_api.post("/change/{model}/{rec_name}", tags=["forms"])
async def onchange_data(
        request: Request,
        model: str,
        rec_name: str,
        field: str
):
    """
    Salva un form
    """
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    content_service = await gateway.content_service_from_record(model, rec_name=rec_name)
    response = await content_service.form_change_handler(field)
    return response


@client_api.post("/change/{model}/", tags=["forms"])
async def onchange_data_new_form(
        request: Request,
        model: str,
        field: str
):
    """
    Salva un form
    """
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    content_service = await gateway.content_service_from_record(model, rec_name="")
    response = await content_service.form_change_handler(field)
    return response


@client_api.post("/data/table/{action_name}", tags=["base"])
async def client_data_table(
        request: Request,
        action_name: str,
        parent: Optional[str] = ""
):
    """
    Ritorna client_form_resource
    """
    url = f"{get_settings().service_url}/data/table/{action_name}"
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    content_service_tmp = await gateway.empty_content_service()
    submitted_data = await request.json()
    data = content_service_tmp.eval_table_processing(submitted_data)
    params = request.query_params.__dict__['_dict'].copy()
    params['container_act'] = "s"
    res_content = await gateway.post_remote_object(
        url, params=params, data=data)
    data_list = await content_service_tmp.process_data_table(res_content.get("content").get("data"), submitted_data)
    resp = {
        "draw": data['draw'] + 1,
        "recordsTotal": res_content.get("content").get("recordsTotal"),
        "recordsFiltered": res_content.get("content").get("recordsFiltered"),
        "data": data_list
    }
    return await gateway.complete_json_response(resp)


@client_api.post("/reorder/data/table", tags=["base"])
async def client_data_table(
        request: Request,
):
    """
    Ritorna client_form_resource
    """
    url = f"{get_settings().service_url}/reorder/data/table/"
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    submitted_data = await request.json()
    res_content = await gateway.post_remote_object(
        url, params=request.query_params, data=submitted_data)
    return await gateway.complete_json_response(res_content)


@client_api.post("/data/search/{model}", tags=["base"])
async def client_data_table_search(
        request: Request,
        model: str,
        parent: Optional[str] = ""
):
    """
    Ritorna client_form_resource
    """
    url = f"{self.local_settings.service_url}/data/search/{model}"
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    submitted_data = await request.json()
    res_content = await gateway.post_remote_object(
        url, params=request.query_params, data=submitted_data)
    return await gateway.complete_json_response(res_content)


@client_api.get("/data/form", tags=["base"])
async def client_form_resource(
        request: Request,
        limit: int,
        select: str,
        type: Optional[str] = 'form',
):
    """
    Ritorna client_form_resource
    """
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    data = await gateway.get_resource_schema_select(type, select)
    return await gateway.complete_json_response(data)


@client_api.get("/print/form/{model}/{rec_name}", tags=["base"])
async def print_form(
        request: Request,
        model: str,
        rec_name: str
):
    """
    Ritorna client_form_resource
    """
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    content_service = await gateway.content_service_from_record(model, rec_name=rec_name)
    response = await content_service.print_form()
    return response


# /client/export/

@client_api.post("/export/{model}/{file_type}", tags=["base"])
async def export_data(
        request: Request,
        model: str,
        file_type: str,
        parent: Optional[str] = ""
):
    """
    Ritorna cun file di esportazione dati
    """
    submitted_data = await request.json()
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    export_service = ExportService.new(gateway=gateway)
    response = await export_service.export_data(model, file_type, submitted_data, parent=parent)
    return response


@client_api.get("/attachment/{data_model}/{uuidpath}/{file_name}", tags=["attachment"])
async def download_attachment(
        request: Request, data_model: str, uuidpath: str, file_name: str
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    content_service = await gateway.content_service_from_record(data_model, rec_name="")
    return await content_service.download_attachment(data_model, uuidpath, file_name)


@client_api.post("/attachment/trash/{model}/{rec_name}", tags=["attachment"])
async def attachment_to_trash(
        request: Request, model: str, rec_name: str
):
    submitted_data = await request.json()
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    content_service = await gateway.content_service_from_record(model, rec_name=rec_name)
    return await content_service.attachment_to_trash(model, rec_name, submitted_data)


@client_api.post("/import/{data_model}", tags=["import"])
async def import_data_model(
        request: Request, data_model: str
):
    submitted_data = await request.json()
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    content_service = await gateway.content_service_from_record(data_model, rec_name="")
    return await content_service.import_data(data_model, submitted_data)


@client_api.post("/export_template/{data_model}", tags=["import"])
async def export_template_for_import(
        request: Request, data_model: str
):
    submitted_data = await request.json()
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    content_service = await gateway.content_service_from_record(data_model, rec_name="")
    return await content_service.template_xls(data_model, submitted_data.get("with_data"))


@client_api.post("/run/calendar_tasks/{cron_task_name}", tags=["Calendar Task"])
async def run_calendar_tasks(
        request: Request,
        cron_task_name: str
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    # content_service = await gateway.empty_content_service()
    return {"status": "done", "name": cron_task_name}


@client_api.get("/polling/calendar_tasks", tags=["Calendar Task"])
async def get_calendar_tasks(
        request: Request
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    list = []
    return list


@client_api.get("/run/clean-app", tags=["Calendar Task"])
async def get_calendar_tasks_completed(
        request: Request
):
    gateway = Gateway.new(request=request, settings=get_settings(), templates=templates)
    content_service = await gateway.empty_content_service()
    return await content_service.clean_records()
