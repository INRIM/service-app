# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import json

from .appinit import *
import ujson
from .core.ServiceMain import ServiceMain
from json import JSONDecodeError


# TODO component base move to frontend
# Actions
@app.post("/action/{name}/{rec_name}", tags=["Actions"])
async def post_action_name_ref(
        request: Request,
        name: str,
        rec_name: str,
        parent: Optional[str] = "",
        iframe: Optional[str] = "",
        container_act: Optional[str] = "",
        apitoken: str = Header(None)

):
    service = ServiceMain.new(request=request)
    dataj = await request.json()
    data = ujson.loads(dataj)
    return await service.service_handle_action(
        action_name=name, data=data, rec_name=rec_name, parent=parent,
        iframe=iframe, execute=True, container_act=container_act)


@app.post("/action/{name}", tags=["Actions"])
async def post_action_name(
        request: Request,
        name: str,
        parent: Optional[str] = "",
        iframe: Optional[str] = "",
        container_act: Optional[str] = "",
        apitoken: str = Header(None)

):
    rec_name = ""
    service = ServiceMain.new(request=request)
    dataj = await request.json()
    data = ujson.loads(dataj)
    return await service.service_handle_action(
        action_name=name, data=data, rec_name=rec_name, parent=parent,
        iframe=iframe, execute=True, container_act=container_act)


# only for Action Builder (maybe)
@app.get("/action/{name}", tags=["Actions"])
async def get_action_name(
        request: Request,
        name: str,
        parent: Optional[str] = "",
        iframe: Optional[str] = "",
        container_act: Optional[str] = "",
        apitoken: str = Header(None)
):
    rec_name = ""
    session = request.scope['ozon'].session
    service = ServiceMain.new(request=request)
    res = await service.service_handle_action(
        action_name=name, rec_name=rec_name, parent=parent, iframe=iframe, container_act=container_act)
    res['breadcrumb'] = session.app['breadcrumb']
    return res


@app.get("/action/{name}/{rec_name}", tags=["Actions"])
async def get_action_ref(
        request: Request,
        name: str,
        rec_name: str,
        parent: Optional[str] = "",
        iframe: Optional[str] = "",
        container_act: Optional[str] = "",
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    service = ServiceMain.new(request=request)
    res = await service.service_handle_action(
        action_name=name, rec_name=rec_name, parent=parent, iframe=iframe, container_act=container_act)
    res['breadcrumb'] = session.app['breadcrumb']
    return res


@app.delete("/action/{name}/{rec_name}", tags=["Actions"])
async def delete_action_name_ref(
        request: Request,
        name: str,
        rec_name: str,
        parent: Optional[str] = "",
        iframe: Optional[str] = "",
        apitoken: str = Header(None)

):
    service = ServiceMain.new(request=request)
    session = request.scope['ozon'].session
    dataj = await request.json()
    data = ujson.loads(dataj)
    res = await service.service_handle_action(
        action_name=name, data=data, rec_name=rec_name, parent=parent, iframe=iframe, execute=True)
    res['breadcrumb'] = session.app['breadcrumb']
    return res


# Component Remote Data and Resources

@app.get("/get_remote_data_select", tags=["Component Remote Data and Resources"])
async def get_remote_data_select(
        request: Request,
        url: str,
        header_key: str,
        header_value_key: str,
        path_value: Optional[str] = "",
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    res = await service.get_remote_data_select(url, path_value, header_key, header_value_key)
    return res


@app.get("/resource/schema/select", tags=["Component Remote Data and Resources"])
async def get_schema_resource_select(
        request: Request,
        otype: str,
        select: str,
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    add_key = ["_id", "rec_name"]
    return await service.service_get_schemas_by_type(
        schema_type=otype, fields=select.split(","), additional_key=add_key)


@app.get("/resource/data/{model_name}", tags=["Component Remote Data and Resources"])
async def get_data_resources(
        request: Request,
        model_name: str,
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    return await service.service_get_data_for_model(model_name)


# Structural Data

@app.get("/layout", tags=["Structural Data"])
async def default_layout(
        request: Request,
        name: Optional[str] = "",
        apitoken: str = Header(None)
):
    service = ServiceMain.new(request=request)
    return await service.service_get_layout(name)


@app.get("/dashboard", tags=["Structural Data"])
async def dashboard(
        request: Request,
        apitoken: str = Header(None)
):
    service = ServiceMain.new(request=request)
    return await service.service_get_dashboard()


@app.get("/form/schema/select", tags=["Structural Data"])
async def get_schema_select(
        request: Request,
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    fields = ['rec_name', 'title']
    return await service.service_get_schemas_by_type(
        schema_type="form", fields=fields)


@app.get("/form/schema/{parent}", tags=["Structural Data"])
async def get_schema_parent(
        request: Request,
        parent: str,
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    return await service.service_get_schemas_by_parent_and_type(
        parent, schema_type="form", fields=[])


@app.get("/schema/{model_name}", tags=["Structural Data"])
async def get_schema_model(
        request: Request,
        model_name: str,
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    return await service.service_get_schema(model_name)


@app.get("/record/{model_name}/{rec_name}", tags=["Structural Data"])
async def get_record_rec_name(
        request: Request,
        model_name: str,
        rec_name: str,
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    return await service.service_get_record(model_name, rec_name)


@app.get("/record/{model_name}", tags=["Core"])
async def get_record(
        request: Request,
        model_name: str,
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    return await service.service_get_record(model_name, "")


@app.get("/models/distinct", tags=["Core"])
async def get_distinct_model(
        request: Request,
        model: Optional[str] = "component",
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    props = request.query_params.__dict__['_dict'].copy()
    query = props.get("domain", "{}")
    domain = service.qe.check_parse_json(query)
    if not isinstance(domain, dict):
        return {
            "status": "error",
            "message": f'Errore Nella codifica del json {domain}  {type(domain)}verifica double quote ',
            "model": model
        }
    res = await service.service_distinct_rec_name_by_model(
        model_name=model, domain=domain, props=props)
    return res


@app.get("/clean/records", tags=["Core"])
async def clean_records(
        request: Request,
        apitoken: str = Header(None)
):
    """
    Remove all recerds in all collections with 'deleted' timestam grater than now.
    """
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    if session.is_admin:
        res = await service.clean_all_to_delete_action()
    else:
        res = {"status": "err"}
    return res


@app.post("/data/table/{action_name}", tags=["Table Data"])
async def post_table_data(
        request: Request,
        action_name: str,
        parent: Optional[str] = "",
        container_act: Optional[str] = "",
        apitoken: str = Header(None)

):
    rec_name = ""
    service = ServiceMain.new(request=request)
    dataj = await request.json()
    data = ujson.loads(dataj)
    res = await service.service_handle_action(
        action_name=action_name, data=data, rec_name=rec_name, parent=parent,
        iframe=False, execute=True, container_act=container_act)
    return res


@app.post("/reorder/data/table", tags=["Table Data reorder"])
async def post_table_data_reorder(
        request: Request,
        apitoken: str = Header(None)
):
    rec_name = ""
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    dataj = await request.json()
    data = ujson.loads(dataj)
    return await service.service_reorder_record(data)


@app.post("/data/search/{model}", tags=["Search Engine"])
async def post_table_search(
        request: Request,
        model: str,
        parent: Optional[str] = "",
        apitoken: str = Header(None)

):
    rec_name = ""
    session = request.scope['ozon'].session
    # service = ServiceMain.new(request=request)
    data = await request.json()
    session.queries[model] = ujson.dumps(data, escape_forward_slashes=False, ensure_ascii=False)
    return {"link": "#"}  # reload page


@app.post("/export_data/{model}", tags=["Component Remote Data and Model for export file"])
async def get_export_data(
        request: Request,
        model: str,
        parent: Optional[str] = "",
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    dataj = await request.json()
    data = ujson.loads(dataj)
    res = await service.export_data(model, data, parent_name=parent)
    return res


@app.post("/attachment/trash/{model}/{rec_name}", tags=["Attachments"])
async def attachment_to_trash(
        request: Request,
        model: str,
        rec_name: str,
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    dataj = await request.json()
    data = ujson.loads(dataj)
    res = await service.attachment_to_trash(model, rec_name, data)
    return res


@app.get("/mail_template/{model}", tags=["Mail"])
async def get_mail_template(
        request: Request,
        model: str,
        parent: Optional[str] = "",
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    res = await service.get_mail_template(model, template_name="")
    return res


@app.get("/mail_template/{model}/{template_name}", tags=["Mail"])
async def get_mail_template_with_name(
        request: Request,
        model: str,
        template_name: Optional[str] = "",
        parent: Optional[str] = "",
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    res = await service.get_mail_template(model, template_name=template_name)
    return res


@app.get("/mail_server/{server_name}", tags=["Mail"])
async def get_mail_server(
        request: Request,
        server_name: str,
        apitoken: str = Header(None)
):
    session = request.scope['ozon'].session
    session.app['save_session'] = False
    service = ServiceMain.new(request=request)
    res = await service.get_mail_server_out(server_name)
    return res
