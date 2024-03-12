# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import logging
from typing import Optional, Union

import ujson
from fastapi import (
    FastAPI,
    Request,
    Header,
)
from fastapi.responses import (
    JSONResponse,
)

from core.ExportService import ExportService
from core.Gateway import Gateway
from settings import get_settings, templates

logger = logging.getLogger(__name__)

client_api = FastAPI(
    title=f"{get_settings().module_name} Client",
    description=get_settings().description,
    version=get_settings().version,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)


@client_api.post("/fast_search", tags=["admin client"])
async def fast_search_action(
        request: Request,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Handle fast search action
    :param request:
    :param authtoken:
    :param apitoken:
    :return:
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    submitted_data = await gateway.load_post_request_data()
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    logger.debug(submitted_data)
    field = submitted_data["field"]
    content_service = await gateway.content_service_from_record(
        submitted_data["fast_serch_model"], rec_name=""
    )
    response = await content_service.fast_search_eval(
        submitted_data.copy(), field
    )
    return response


@client_api.post("/modal/action", tags=["admin client"])
async def modal_action(
        request: Request,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Ecexute action in modal view
    :param request:
    :param authtoken:
    :param apitoken:
    :return:
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    submitted_data = await gateway.load_post_request_data()

    # if not dict is error
    if isinstance(submitted_data, JSONResponse):
        return submitted_data
    response = {}
    if submitted_data.get("related_action"):
        related_action = submitted_data.pop("related_action")
        response_data, response, content_service = await gateway.post_data(
            submitted_data.copy(), ui_response=False)
        if "error" in response_data.get("status", ""):
            logger.error(f"modal get  {response_data}")
            return await content_service.form_post_complete_response(
                response_data, response
            )
        if related_action.get("todo") == "new_row":
            form_data = response_data.get("data", {})
            d_fields = ujson.loads(related_action.get("default_fields", "{}"))
            logger.info(d_fields)
            params = "&".join(
                [f"{v}={form_data.get(k)}" for k, v in d_fields.items()])
            action_url = f"{related_action.get('url', '')}?{params}"
            response = await gateway.server_get_action(
                url_action=action_url, modal=True
            )
    else:
        if submitted_data.get("action"):
            act = submitted_data.get("action")
            url_act = submitted_data.get("url")
            model = submitted_data.get("model")
            rec_name = submitted_data.get("rec_name")
            logger.info(submitted_data)
            if act == "copy":
                data = await gateway.get_record_data(model, rec_name)
                data.pop("_id")
                response = await gateway.post_remote_object(
                    url_act, data=data)
                response_data = response.get("content", {})
                if "error" in response_data.get("status", ""):
                    cs = await gateway.empty_content_service()
                    logger.error(f"modal get  {response_data}")
                    return await cs.form_post_complete_response(
                        response_data, response
                    )
                response = await gateway.server_get_action(
                    url_action=response_data.get("link"),
                    modal=True
                )
            elif act == "remove":
                response_data = await gateway.post_remote_object(
                    url_act, data={})
                if "error" in response_data.get("status", ""):
                    cs = await gateway.empty_content_service()
                    logger.error(f"modal get  {response_data}")
                    return await cs.form_post_complete_response(
                        response_data, response
                    )
                response = await gateway.complete_json_response(
                    {"link": "#", "reload": True, "status": "ok"}
                )
        else:
            if submitted_data.get("url"):
                action_url = submitted_data.get("url")
            else:
                action_url = f"/action/{submitted_data.get('action')}/{submitted_data.get('record')}"
            response = await gateway.server_get_action(
                url_action=action_url, modal=True
            )
    return response


@client_api.get("/grid/{key}/{model}/rows/", tags=["admin client"])
async def client_grid_rows(
        request: Request,
        key: str,
        model: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Datagrid load rows
    :param request:
    :param key:
    :param model:
    :param authtoken:
    :param apitoken:
    :return:
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    res = await gateway.compute_datagrid_rows(key, model, rec_name="")
    return res


@client_api.get("/grid/{key}/{model}/rows/{rec_name}", tags=["admin client"])
async def client_grid_rows_data(
        request: Request,
        key: str,
        model: str,
        rec_name: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    datagrid add new row
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    res = await gateway.compute_datagrid_rows(key, model, rec_name=rec_name)
    return res


@client_api.post(
    "/grid/{key}/{model}/{num_rows}/newrow", tags=["admin client"]
)
async def client_grid_new_row(
        request: Request,
        key: str,
        model: str,
        num_rows: int,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    datagrid add new row
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    submitted_data = await gateway.load_post_request_data()
    res = await gateway.compute_datagrid_add_row(
        key, num_rows, model, rec_name="", data=submitted_data
    )
    return res


@client_api.post("/change/{model}/{rec_name}", tags=["forms"])
async def onchange_data(
        request: Request,
        model: str,
        rec_name: str,
        field: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    evaluate form chage
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.content_service_from_record(
        model, rec_name=rec_name
    )
    response = await content_service.form_change_handler(field)
    return response


@client_api.post("/change/{model}/", tags=["forms"])
async def onchange_data_new_form(
        request: Request,
        model: str,
        field: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    evaluate form chage in new form
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.content_service_from_record(
        model, rec_name=""
    )
    response = await content_service.form_change_handler(field)
    return response


@client_api.post("/data/table/{action_name}", tags=["base"])
async def client_data_table(
        request: Request,
        action_name: str,
        parent: Optional[str] = "",
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Return a structure for data table
    """
    url = f"{get_settings().service_url}/data/table/{action_name}"
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service_tmp = await gateway.empty_content_service()
    submitted_data = await request.json()

    data = await content_service_tmp.eval_table_processing(submitted_data)
    params = request.query_params.__dict__["_dict"].copy()
    params["container_act"] = "n"
    res_content = await gateway.post_remote_object(
        url, params=params, data=data
    )
    data_list = await content_service_tmp.process_data_table(
        res_content.get("content").get("data"), submitted_data
    )
    resp = {
        "draw": data["draw"] + 1,
        "recordsTotal": res_content.get("content").get("recordsTotal"),
        "recordsFiltered": res_content.get("content").get("recordsFiltered"),
        "data": data_list,
    }
    return await gateway.complete_json_response(resp)


@client_api.post("/reorder/data/table", tags=["base"])
async def client_data_table(
        request: Request,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Order data in table
    """
    url = f"{get_settings().service_url}/reorder/data/table"
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    submitted_data = await request.json()
    res_content = await gateway.post_remote_object(
        url, params=request.query_params, data=submitted_data
    )
    return await gateway.complete_json_response(res_content)


@client_api.post("/data/search/{model}", tags=["base"])
async def client_data_table_search(
        request: Request,
        model: str,
        parent: Optional[str] = "",
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Search data in model
    """
    url = f"{self.local_settings.service_url}/data/search/{model}"
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    submitted_data = await request.json()
    res_content = await gateway.post_remote_object(
        url, params=request.query_params, data=submitted_data
    )
    return await gateway.complete_json_response(res_content)


@client_api.get("/data/form", tags=["base"])
async def client_form_resource(
        request: Request,
        limit: int,
        select: str,
        type: Optional[str] = "form",
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Ritorna client_form_resource
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    data = await gateway.get_resource_schema_select(type, select)
    return await gateway.complete_json_response(data)


@client_api.get("/print/form/{model}/{rec_name}", tags=["base"])
async def print_form(
        request: Request,
        model: str,
        rec_name: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Print pdf of a form if is designed in form builder

    :param model:  model name (form api name)
    :param rec_name: record name
    :param authtoken: user token that execute request
    :param apitoken: api key that execute request
    :return: blob file
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.content_service_from_record(
        model, rec_name=rec_name
    )
    response = await content_service.print_form()
    return response


# /client/export/


@client_api.post("/export/{model}/{file_type}", tags=["base"])
async def export_data(
        request: Request,
        model: str,
        file_type: str,
        parent: Optional[str] = "",
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Export a file of data for specific form (model)

    default body: {query:{}}

    :param model: model name (form api name)
    :param file_type: json, xls, csv
    :param authtoken: user token that execute request
    :param apitoken: api key that execute request
    :return: blob file
    """
    submitted_data = await request.json() or {}
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    export_service = ExportService.new(gateway=gateway)
    response = await export_service.export_data(
        model, file_type, submitted_data, parent=parent
    )
    return response


@client_api.get(
    "/attachment/{data_model}/{uuidpath}/{file_name}", tags=["attachment"]
)
async def download_attachment(
        request: Request,
        data_model: str,
        uuidpath: str,
        file_name: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Download an attachment file

    :param request:
    :param data_model:
    :param uuidpath:
    :param file_name:
    :param authtoken:
    :param apitoken:
    :return:
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.content_service_from_record(
        data_model, rec_name=""
    )
    return await content_service.download_attachment(
        data_model, uuidpath, file_name
    )


@client_api.post("/attachment/trash/{model}/{rec_name}", tags=["attachment"])
async def attachment_to_trash(
        request: Request,
        model: str,
        rec_name: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Delete attachment file and move it in a trash loction

    :param request:
    :param model:
    :param rec_name:
    :param authtoken:
    :param apitoken:
    :return:
    """
    submitted_data = await request.json()
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.content_service_from_record(
        model, rec_name=rec_name
    )
    return await content_service.attachment_to_trash(
        model, rec_name, submitted_data
    )


@client_api.post("/attachment/unlink/{model}/{rec_name}", tags=["attachment"])
async def attachment_unlink(
        request: Request,
        model: str,
        rec_name: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Unlink attachment file from record

    :param request:
    :param model:
    :param rec_name:
    :param authtoken:
    :param apitoken:
    :return:
    """
    submitted_data = await request.json()
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.content_service_from_record(
        model, rec_name=rec_name
    )
    return await content_service.attachment_unlink(
        model, rec_name, submitted_data
    )


@client_api.post(
    "/attachment/copy/{model}/{rec_name}/{field}/{dest}", tags=["attachment"]
)
async def attachment_copy(
        request: Request,
        model: str,
        rec_name: str,
        field: str,
        dest: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Copy attachments file from record model.rec_name to dest folder

    :param request:
    :param model:
    :param rec_name:
    :param dest:
    :param authtoken:
    :param apitoken:
    :return:JsonResponse with list of data for attachment field
    """
    submitted_data = await request.json()
    gateway = Gateway.new(
        request=request, settings=get_settings(), emplates=templates
    )
    content_service = await gateway.content_service_from_record(
        model, rec_name=rec_name
    )
    return await content_service.copy_attachments(model, rec_name, field, dest)


@client_api.post("/import/{data_model}", tags=["import"])
async def import_data_model(
        request: Request,
        data_model: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Execute massive import data from excel file

    :param request:
    :param data_model:
    :return:
    """
    submitted_data = await request.json()
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.content_service_from_record(
        data_model, rec_name=""
    )
    return await content_service.import_data(data_model, submitted_data)


@client_api.post("/export_template/{data_model}", tags=["import"])
async def export_template_for_import(
        request: Request,
        data_model: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Export template data sructure in excel compliance
    for massive import data.

    :param request:
    :param data_model:
    :param authtoken:
    :param apitoken:
    :return:
    """
    submitted_data = await request.json()
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.content_service_from_record(
        data_model, rec_name=""
    )
    return await content_service.template_xls(
        data_model, submitted_data.get("with_data")
    )


@client_api.post("/run/calendar_tasks/{task_name}", tags=["Calendar Task"])
async def run_calendar_tasks(
        request: Request,
        task_name: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Trigger calendar task by name

    :param request:
    :param task_name:
    :param authtoken:
    :param apitoken:
    :return:
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.empty_content_service()
    return await content_service.execute_task(task_name)


@client_api.get("/polling/calendar_tasks", tags=["Calendar Task"])
async def get_calendar_tasks(request: Request):
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.empty_content_service()
    return await content_service.polling_calendar_tasks()


@client_api.get("/run/clean-app", tags=["Cron clean "])
async def clean_records(
        request: Request,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    Trigger clean app data,
    - remove all data deleted and expired
    - remove old expired session records
    :param request:
    :param authtoken:
    :param apitoken:
    :return:
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.empty_content_service()
    return await content_service.clean_records()


@client_api.post(
    "/send/mail/{model}/{rec_name}/{tmp_name}", tags=["Calendar Task"]
)
async def send_mail(
        request: Request,
        model: str,
        rec_name: str,
        tmp_name: str,
        authtoken: Union[str, None] = Header(default=None),
        apitoken: Union[str, None] = Header(default=None),
):
    """
    trigger send mail by model and record with specific template name

    :param request:
    :param model:
    :param rec_name:
    :param tmp_name:
    :param authtoken:
    :param apitoken:
    :return:
    """
    gateway = Gateway.new(
        request=request, settings=get_settings(), templates=templates
    )
    content_service = await gateway.content_service_from_record(
        model, rec_name=rec_name
    )
    data = content_service.content.get("data", {})
    return await content_service.send_email(data, tmp_name=tmp_name)
