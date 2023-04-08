# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import json
import sys
from typing import Optional

import requests

from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.responses import RedirectResponse, FileResponse
from .main.widgets_table_form import TableFormWidget
from .main.widgets_table import TableWidget
from .main.widgets_form import FormIoWidget
from .main.widgets_content import PageWidget
from .main.widgets_form_builder import FormIoBuilderWidget
from .main.widgets_layout import LayoutWidget
from .main.widgets_base import WidgetsBase
from .main.widgets_dashboard import DashboardWidget
from .main.base.basicmodel import *
from .main.base.base_class import BaseClass, PluginBase
from .main.base.utils_for_service import *
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from .FormIoBuilder import FormIoBuilder
import httpx
import logging
import ujson
import pdfkit
from datetime import datetime, timedelta
import aiofiles
import uuid
from fastapi.concurrency import run_in_threadpool
from aiopath import AsyncPath
from core.cache.cache import get_cache
import asyncio

logger = logging.getLogger(__name__)


class ContentService(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        if cls not in cls.plugins:
            cls.plugins.append(cls())


class ContentServiceBase(ContentService):

    @classmethod
    def create(cls, gateway, remote_data):
        self = ContentServiceBase()
        self.init(gateway, remote_data)
        return self

    def init(self, gateway, remote_data):
        self.gateway = gateway
        self.remote_data = remote_data
        self.content = remote_data.get("content", {})
        self.request = gateway.request
        self.local_settings = gateway.local_settings
        self.templates = gateway.templates
        self.session = gateway.session.copy()
        self.app_settings = self.session.get('app', {}).get(
            "settings", self.local_settings.dict()).copy()
        self.layout = None
        self.is_create = False
        if self.content.get("mode", "") == "form":
            create_datetime = remote_data.get("content").get("data").get(
                "create_datetime", None) is None
            update_datetime = remote_data.get("content").get("data").get(
                "update_datetime", None) is None
            if create_datetime is None and update_datetime is None:
                self.is_create = True
        logger.debug(f"IS CREATE == {self.is_create}")
        self.attachments_to_save = []
        self.component_filters = [
            {
                "id": "list_order",
                "input": "text",
                "label": "List Order",
                'default_operator': 'equal',
                "operators": ["equal", "not_equal", "greater",
                              "greater_or_equal", "less", "less_or_equal",
                              "in",
                              "not_in"],
                "type": "integer",
                "value_separator": "|"
            },
            {"id": "deleted", "label": "Eliminato",
             "operators": ["equal", "not_equal", "greater"],
             'default_operator': 'equal',
             "input": "text", "type": "integer"},
            {"id": "rec_name", "label": "Name", 'default_operator': 'contains',
             "type": "string"},
            {"id": "title", "label": "Title", 'default_operator': 'contains',
             "type": "string"},
            {"id": "projectId", "label": "Progetto",
             'default_operator': 'contains', "type": "string"},
            {"id": "type", "label": "Tipo", 'default_operator': 'contains',
             "type": "string"},
            {"id": "data_model", "label": "Parent Model",
             'default_operator': 'equal', "type": "string"},
            {
                "id": "sys",
                "input": "radio",
                "label": "Di Sistema",
                'type': 'boolean',
                'values': {
                    "true": 'Yes',
                    "false": 'No'
                },
                'operators': ['equal']
            },
            {
                "id": "active",
                "input": "radio",
                "label": "Attivo",
                'type': 'boolean',
                'values': {
                    "true": 'Yes',
                    "false": 'No'
                },
                'operators': ['equal']
            }
        ]

    async def make_page(self):
        logger.debug("Make Page")
        if self.content.get("builder") and self.content.get('mode') == "form":
            logger.info("FormIoBuilder")
            content = self.remote_data.get('content')
            c_type = content.get('component_type')
            list_models = await self.gateway.get_list_models(
                domain={"data_model": "", "type": c_type},
                compute_label="type,title")
            parent_model_schema = {}
            if content.get("data"):
                parent_model = content.get("data").get("data_model")
                parent_model_schema = {}
                if parent_model:
                    parent_model_schema = await self.gateway.get_schema(
                        parent_model)
            form_builder = FormIoBuilder.new(
                request=self.request, session=self.session,
                settings=self.app_settings.copy(),
                response=self.remote_data,
                templates=self.templates,
                list_models=list_models,
                parent_model_schema=parent_model_schema
            )
            content = await form_builder.form_builder()
            if self.request.query_params.get("iframe"):
                return content
        elif "cards" in self.content:
            logger.debug(f"Make Page -> Dashboard")
            dashboard = DashboardWidget.new(
                templates_engine=self.templates, session=self.session,
                request=self.request,
                settings=self.app_settings.copy(),
                content=self.content.copy()
            )
            content = await run_in_threadpool(
                lambda: dashboard.make_dashboard())
            logger.debug("Make Dashboard Done")
        else:
            logger.info(f"Make Page -> compute_{self.content.get('mode')}")
            content = await getattr(
                self, f"compute_{self.content.get('mode')}")()
        layout = await self.get_layout()
        await run_in_threadpool(
            lambda: layout.make_context_button(self.content))
        await run_in_threadpool(lambda: layout.rows.append(content))
        logger.debug("Make Page Done")
        return await run_in_threadpool(lambda: layout.render_layout())

    async def compute_list(self):
        logger.debug("Compute Table List")
        return await self.render_table()

    async def compute_form(self, modal=False, url=""):
        editing = self.session.get('app').get("builder", False)
        logger.info(
            f"Edit mode {editing} Compute Form "
            f"modal {modal} url {url}"
        )

        page = FormIoWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request,
            settings=self.app_settings.copy(),
            content=self.content.copy(),
            schema=self.content.get('schema', {}).copy(),
            modal=modal,
            modal_form_url=url
        )
        data = {}
        if self.content.get('data'):
            data = self.content.get('data', {}).copy()
        await run_in_threadpool(lambda: page.init_form(data.copy()))
        await self.eval_data_src_componentes(
            page.components_ext_data_src, data=data)

        if page.tables:
            for table in page.tables:
                await self.eval_table(table, parent=page.rec_name)

        await self.eval_search_areas(page)

        form = await run_in_threadpool(lambda: page.make_form())

        return form

    async def eval_data_src_component(self, component, data={}):
        logger.info(f"eval {component.key}")
        editing = self.session.get('app').get("builder")
        if component.dataSrc == "custom":
            key = component.data.get("custom")
            dat = data.get(key, [])
            if not dat and data.get("data_value", {}).get(key):
                dat = data.get("data_value", {}).get(key, [])
            component.resources = dat

            component.make_resource_list()
        else:
            cache = await get_cache()
            use_cahe = True
            if (
                    component.properties.get("domain") and
                    not component.properties.get("domain") == "{}"
            ):
                use_cahe = False
            memc = await cache.get(
                "components_ext_data_src",
                f"{component.key}:{component.dataSrc}:{component.valueProperty}")
            if memc and not editing and use_cahe:
                logger.debug(
                    f"use cache {component.key}  {component.dataSrc}")
                component.raw = memc
            else:
                if component.dataSrc in ["resource", "form"]:
                    component.resources = await self.gateway.get_ext_submission(
                        component.resource_id,
                        params=component.properties.copy()
                    )
                elif component.dataSrc == "url":
                    if component.idPath:
                        component.path_value = self.session.get(
                            component.idPath, component.idPath)
                    if "http" not in component.url and "https" not in component.url:
                        url = f"{self.local_settings.service_url}{component.url}"
                        res = await self.gateway.get_remote_object(
                            url, params=component.properties.copy())
                        if res.get("status") and res.get(
                                "status") == "error":
                            component.resources = [
                                {"rec_name": res.get("status"),
                                 "title": res.get("message")}]
                        else:
                            component.resources = res.get(
                                "content", {}).get("data", [])[:]
                    else:
                        component.resources = await self.gateway.get_remote_data_select(
                            component.url, component.path_value,
                            component.header_key,
                            component.header_value_key
                        )
                    if component.selectValues and component.valueProperty:
                        if isinstance(
                                component.resources,
                                dict) and component.resources.get("result"):
                            tmp_res = component.resources.copy()
                            component.resources = []
                            component.resources = tmp_res['result'].get(
                                component.selectValues)
                            component.selected_id = tmp_res['result'].get(
                                component.valueProperty)
                    elif component.selectValues and isinstance(
                            component.resources, dict):
                        component.resources = component.resources.get(
                            component.selectValues)
                component.make_resource_list()
                if component.raw['data']['values']:
                    await cache.clear(
                        "components_ext_data_src",
                        f"{component.key}:{component.dataSrc}:{component.valueProperty}")
                    await cache.set(
                        "components_ext_data_src",
                        f"{component.key}:{component.dataSrc}:{component.valueProperty}",
                        component.raw, expire=800)  # 8

    async def eval_data_src_componentes(
            self, components_ext_data_src, data={}):
        if components_ext_data_src:
            for component in components_ext_data_src:
                await self.eval_data_src_component(component, data=data)

    async def create_folder(self, base_upload, model_data, sub_folder=""):
        form_upload = f"{base_upload}/{model_data}"
        if sub_folder:
            form_upload = f"{base_upload}/{model_data}/{sub_folder}"
        await AsyncPath(form_upload).mkdir(parents=True, exist_ok=True)
        return form_upload

    async def eval_datagrid_response(
            self, data_grid, render=False, num_rows=0):
        results = {"rows": [], 'showAdd': data_grid.add_enabled}

        # row = data_grid.rows[-1]
        def add_in_result(row_to_add, render_row=False):
            if render_row:
                rendered_row = row_to_add.render(log=False)
                results['rows'].append(rendered_row)
            else:
                results['rows'].append(row_to_add)

        if num_rows == 0:
            for row in data_grid.rows:
                add_in_result(row, render_row=render)
        else:
            row = data_grid.rows[-1]
            add_in_result(row, render_row=render)
        return results

    async def compute_datagrid_rows(self, key):
        logger.info(f"compute_grid_rows {key}")
        page = FormIoWidget.new(
            templates_engine=self.templates,
            session=self.session,
            request=self.request,
            settings=self.app_settings.copy(),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        data = {}
        if self.content.get('data'):
            data = self.content.get('data', {}).copy()
        await run_in_threadpool(lambda: page.init_form(data))
        data_grid = await run_in_threadpool(lambda: page.grid_rows(key))

        await self.eval_data_src_componentes(
            page.components_ext_data_src, data=data)

        if data_grid.tables:
            for table in data_grid.tables:
                await self.eval_table(table)

        res = await self.eval_datagrid_response(data_grid, render=True)

        return res

    async def compute_datagrid_add_row(
            self, key, num_rows, data={}):
        logger.info(f"compute_grid_add_row")

        page = FormIoWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request,
            settings=self.app_settings.copy(),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        await run_in_threadpool(lambda: page.init_form(data))
        page.builder.compute_data()
        data = page.builder.main.form_data
        data_grid = await run_in_threadpool(
            lambda: page.grid_add_row(key, num_rows))
        await self.eval_data_src_componentes(
            page.components_ext_data_src, data=data)
        if data_grid.tables:
            for table in data_grid.tables:
                await self.eval_table(table)

        res = await self.eval_datagrid_response(
            data_grid, render=True, num_rows=num_rows)

        return res

    async def print_form(self):
        logger.info(f"print_form")
        page = FormIoWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request,
            settings=self.app_settings.copy(),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        await run_in_threadpool(
            lambda: page.init_form(self.content.get('data').copy()))
        report_html = await run_in_threadpool(
            lambda: page.render_report_html())
        dt_report = datetime.now().strftime(
            self.local_settings.server_datetime_mask
        )
        file_report = f"/tmp/{page.title}_{dt_report}.pdf"
        options = {
            'page-size': 'A4',
            'margin-top': '3mm',
            'margin-right': '3mm',
            'margin-bottom': '3mm',
            'margin-left': '3mm',
            'disable-smart-shrinking': '',
            'dpi': '400',
            'print-media-type': '',
            "zoom": "1",
            'encoding': "UTF-8",
            'quiet': ''
        }
        options = await run_in_threadpool(
            lambda: page.handle_header_footer(options))
        pkit = pdfkit.PDFKit(report_html, 'string', options=options,
                             verbose=True)
        logger.info(f"pkit -->  {' '.join(pkit.command())}")
        await run_in_threadpool(lambda: pkit.to_pdf(file_report))
        return FileResponse(file_report)

    async def fast_search_hanlde_query(self, page, data_model, fs_model):
        data = page.builder.main.form_data
        res = {"query": {}}
        page.form_compute_change_form()
        await self.eval_data_src_componentes(
            page.components_change_ext_data_src)

        comp_q = []
        for comp in page.builder.components_logic:
            if comp.properties.get("query"):
                try:
                    q = comp.properties.get("query")
                    if isinstance(q, str):
                        jval = eval(q)
                    elif isinstance(q, dict):
                        jval = q
                    if jval:
                        comp_q.append(jval)
                except Exception as e:
                    logger.info(f'ex {e} ', exc_info=True)
                    pass
        payload = {
            "form": data.copy(),
            "fast_serch_model": fs_model,
            "data_model": data_model,
            "query_fields": comp_q
        }
        res = await self.gateway.post_remote_object(
            "/data/fast_search_eval", data=payload
        )

        return res

    # TODO FIX fast search (24/01/2022)
    async def fast_search_eval(self, data, field) -> list:
        logger.info("eval schema")
        if "rec_name" not in data:
            data['data']['rec_name'] = "fs"
        page = FormIoWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request,
            settings=self.app_settings.copy(),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        await run_in_threadpool(lambda: page.init_form(data['data'].copy()))
        await self.eval_data_src_componentes(page.components_ext_data_src,
                                             data=data['data'])

        res = await self.fast_search_hanlde_query(
            page, data_model=data.get('data_model'), fs_model=page.model)

        return await self.gateway.complete_json_response(
            {"query": res.get('content', {}).get('data', {})}
        )

    # TODO fix see form_post
    async def form_change_handler(self, field) -> list:
        logger.info(f"Compute Form Change {self.content.get('model')}")
        modal = False
        if self.request.query_params.get("miframe"):
            modal = True
        self.session = await self.gateway.get_session()
        self.app_settings = self.session.get(
            'app', {}).get("settings", self.local_settings.dict()).copy()
        submitted_data = await self.request.json()
        if "rec_name" in submitted_data and not submitted_data.get(
                "rec_name") == "":
            allowed = self.gateway.name_allowed.match(
                submitted_data.get("rec_name"))
            if not allowed:
                logger.error(f"name {submitted_data.get('rec_name')}")
                err = {
                    "status": "error",
                    "message": f"Errore nel campo name {submitted_data.get('rec_name')} caratteri non consentiti",
                    "model": submitted_data.get('data_model')
                }
                return await self.form_post_complete_response(err, None)

        page = FormIoWidget.new(
            templates_engine=self.templates,
            session=self.session,
            request=self.request,
            settings=self.app_settings.copy(),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        await run_in_threadpool(lambda: page.init_form(submitted_data))
        await self.eval_data_src_componentes(page.components_ext_data_src,
                                             data=submitted_data)

        if page.tables:
            for table in page.tables:
                await self.eval_table(table, parent=page.rec_name)

        await self.eval_search_areas(page)

        resp = await page.render_change_components(self)

        return await self.gateway.complete_json_response(resp)

    async def form_post_handler(self, submitted_data) -> dict:
        logger.info(f"form_post_handler")
        page = FormIoWidget.new(
            templates_engine=self.templates,
            session=self.session,
            request=self.request,
            settings=self.app_settings.copy(),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        if "rec_name" in submitted_data and not submitted_data.get(
                "rec_name") == "":
            allowed = self.gateway.name_allowed.match(
                str(submitted_data.get("rec_name")))
            if not allowed:
                logger.error(f"name {submitted_data.get('rec_name')}")
                err = {
                    "status": "error",
                    "message": f"Errore nel campo name "
                               f"{submitted_data.get('rec_name')} "
                               f"caratteri non consentiti",
                    "model": submitted_data.get('data_model')
                }
                return await self.form_post_complete_response(err, None)
        # logger.info(self.session)
        await run_in_threadpool(lambda: page.init_form(submitted_data))
        submit_data = await self.handle_attachment(
            page.uploaders, submitted_data.copy(),
            self.content.get("data", {}).copy())
        await run_in_threadpool(lambda: page.init_form(submit_data))
        await self.eval_data_src_componentes(page.components_ext_data_src,
                                             data=submitted_data)

        return await run_in_threadpool(lambda: page.form_compute_submit())

    async def before_submit(self, remote_data):
        return remote_data.copy()

    async def after_form_post_handler(self, remote_data, submitted_data):
        return remote_data.copy()

    async def form_post_complete_response(self, response_data, response):
        logger.info(f"form post complete make response")
        if "error" in response_data.get('status', ""):
            widget = WidgetsBase.create(
                templates_engine=self.templates, session=self.session,
                request=self.request)
            if self.gateway.session['app'].get('act_builder'):
                return widget.response_ajax_notices(
                    "error", f"builder_alert", response_data['message'])
            else:
                return widget.response_ajax_notices(
                    "error", f"{response_data['model']}_alert",
                    response_data['message'])
        elif "action" in response_data and response_data.get(
                "action") == "redirect":
            url = response_data.get("url")
            return await self.gateway.complete_json_response({
                "link": url,
                "reload": True,
                "status": "ok"
            })
        else:
            await self.check_and_save_attachment()
            return await self.gateway.complete_json_response(response_data,
                                                             orig_resp=response)

    async def check_and_save_attachment(self):
        if self.attachments_to_save:
            logger.info("save attachment")
            for attachment in self.attachments_to_save:
                await self.move_attachment(attachment)

    async def get_layout(self, name="") -> LayoutWidget:
        logger.debug(f"load layout {name}")
        logger.debug(
            f"content breadcrumb: {self.remote_data.get('breadcrumb')}")
        url = f"{self.local_settings.service_url}/layout"
        if name:
            url = f"{url}?name={name}"
        schema_layout = await self.gateway.get_remote_object(url)
        layout = LayoutWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request,
            settings=self.app_settings.copy(),
            content=schema_layout,
            schema=schema_layout.get('schema'),
            breadcrumb=self.remote_data.get('breadcrumb', [])
        )
        await run_in_threadpool(lambda: layout.init_layout())
        return layout

    async def eval_search_areas(self, widget):
        if widget.search_areas:
            for search_area in widget.search_areas:
                if search_area.model == "component":
                    search_area.filters = self.component_filters[:]
                else:
                    query = await self.eval_search_area_query(
                        search_area.model, search_area.query)
                    search_area.query = query
                    if not widget.model == search_area.model:
                        filters = await self.get_filters_for_model(
                            search_area.model)
                    else:
                        filters = widget.filters[:]

                    for c_filter in filters:
                        cfilter = c_filter.get_filter_object()
                        # logger.info(f"..form.filters. {cfilter}")
                        search_area.filters.append(cfilter)

                    if not search_area.has_filter("deleted"):
                        search_area.filters.append(
                            {"id": "deleted", "label": "Eliminato",
                             "operators": ["equal", "not_equal", "greater"],
                             "input": "text", "type": "integer"})

                    if not search_area.has_filter("active"):
                        search_area.filters.append(
                            {"id": "active", "label": "Attivo",
                             'values': {"true": 'Yes', "false": 'No'},
                             "input": "radio", "type": "boolean"})

    async def eval_table(self, table, parent="", content={}):
        logger.info(f" table --> {table.action_url} ")
        if not content:
            table_content = await self.gateway.get_remote_object(
                f"{self.local_settings.service_url}{table.action_url}",
                params={"container_act": "s"}
            )
        else:
            table_content = content
        table_config = TableWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.gateway.request, content=table_content.get('content'),
            disabled=False
        )
        await run_in_threadpool(lambda: table_config.init_table())
        await self.eval_data_src_componentes(
            table_config.components_ext_data_src)
        table.columns = table_config.columns.copy()
        table.hide_rec_name = table_config.rec_name_is_meta
        table.meta_keys = table_config.columns_meta_list[:]
        table.form_columns = table_config.form_columns.copy()
        table.filters = table_config.filters[:]
        table.parent = parent

    async def eval_search_area_query(self, model, query_prop):
        logger.info(f"eval_search_area_query {model}")
        params = self.gateway.request.query_params.__dict__['_dict'].copy()
        base_query = self.content.get("query", {})
        is_domain = self.content.get("is_domain_query", {})
        query = query_prop
        session_query = self.session.get('app')['queries'].get(model, {})
        if params.get('container_act') and session_query and not query_prop:
            query = session_query
        elif base_query and not is_domain and not query_prop:
            query = base_query
        logger.debug(f"eval_search_area_query query --> {query}")
        return query

    async def render_table(self):
        logger.debug("Render Table")
        # TODO prepare and Render Page -No Data-
        widget = TableFormWidget.new(
            templates_engine=self.templates,
            session=self.gateway.session, request=self.gateway.request,
            content=self.content
        )
        await run_in_threadpool(lambda: widget.init_table())
        await self.eval_data_src_componentes(widget.components_ext_data_src)
        if widget.tables:
            for table in widget.tables:
                if self.content.get('mode') == "list":
                    await self.eval_table(table, content=self.remote_data)
                else:
                    await self.eval_table(table)
        if widget.search_areas:
            for search_area in widget.search_areas:
                query = await self.eval_search_area_query(
                    search_area.model, search_area.query)
                search_area.query = query
                if search_area.model == "component":
                    search_area.filters = self.component_filters
                else:
                    filters = table.filters
                    for c_filter in filters:
                        cfilter = c_filter.get_filter_object()
                        # logger.info(f"..form.filters. {cfilter}")
                        if cfilter not in search_area.filters:
                            search_area.filters.append(cfilter)

                    if not search_area.has_filter("deleted"):
                        search_area.filters.append(
                            {"id": "deleted", "label": "Eliminato",
                             "operators": ["equal", "not_equal", "greater"],
                             "input": "text", "type": "integer"})

                    if not search_area.has_filter("active"):
                        search_area.filters.append(
                            {"id": "active", "label": "Attivo",
                             'values': {"true": 'Yes', "false": 'No'},
                             "input": "radio", "type": "boolean"})
        if widget.fast_search_cfg:
            data = json.loads(
                widget.fast_search_cfg.get("data"))
            await self.fast_search_hanlde_query(
                widget, data_model=widget.model,
                fs_model=data.get('data_model'))
        table_view = await run_in_threadpool(lambda: widget.render_widget())
        logger.info(f"Render Table .. Done")
        return table_view

    async def eval_table_processing(self, submitted_data):
        data = {
            "limit": submitted_data['length'],
            "skip": submitted_data['start'],
            "sort": "",
            "query": {}
        }
        columns = submitted_data['columns']
        cols_list = []
        for col in columns:
            cols_list.append(col['data'])
        orders = submitted_data['order']
        sort_list = []
        for order in orders:
            field = columns[order['column']]['data']
            dir = order['dir']
            sort_list.append(f"{field}:{dir}")

        data['sort'] = ",".join(sort_list)
        data['fields'] = cols_list
        data['draw'] = submitted_data['draw']
        data['query'] = submitted_data.get('query', {})
        return data

    async def process_data_table(self, list_data, submitted_data):
        logger.debug("process_data_table")
        data = []
        columns = submitted_data['columns']
        cols_list = []
        for col in columns:
            cols_list.append(col['data'])
        new_list = []
        for record in list_data:
            row = {}
            for field in cols_list:
                dat = None
                if "data_value" in record:
                    dat = record['data_value'].get(field, None)
                if dat is None:
                    dat = record.get(field, "")
                row[field] = dat
            if "rec_name" not in cols_list:
                row["rec_name"] = record.get("rec_name")
            row["row_action"] = record.get("row_action")
            new_list.append(row.copy())
        return new_list[:]

    async def clean_records(self):
        response = await self.gateway.get_remote_object("/clean/records")
        return response

    async def polling_calendar_tasks(self):
        response = await self.gateway.get_remote_object("/get/calendar_tasks")
        return response

    async def execute_task(self, task_name):
        caledar_data = await self.gateway.get_remote_object(
            f"/calendar_tasks/{task_name}")
        return await self.update_tasks(task_name, caledar_data,
                                       status={"status": "done"})

    async def update_tasks(self, task_name, caledar_data,
                           status={"status": "done"}):
        logger.info(f" {task_name}")
        if not caledar_data:
            logger.error(f"execute_tasks {task_name} no data")
            status['status'] = "error"
        response = await self.gateway.post_remote_object(
            f"/update/calendar_tasks/{task_name}", data=status
        )
        return response

    async def get_filters_for_model(self, model):
        logger.debug(f"get_filters_for_model {model}")
        if not model == "component":
            server_response = await self.gateway.get_record(
                model, ""
            )
            content = server_response.get('content')
            form = FormIoWidget.new(
                templates_engine=self.templates, session=self.session,
                request=self.request, settings=self.local_settings,
                content=content.copy(),
                schema=content.get('schema').copy()
            )
            await run_in_threadpool(lambda: form.init_form({}))
            await self.eval_data_src_componentes(form.components_ext_data_src)
            # logger.info(f"..form.filters. {form.filters}")
            return form.filters
        else:
            return self.component_filters

    def compute_builder_data(self, list_data):
        return FormIoBuilder.compute_builder_data(list_data)
