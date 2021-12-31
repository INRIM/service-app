# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
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
from .FormIoBuilder import FormIoBuilder
import httpx
import logging
import ujson
import pdfkit
from html2docx import html2docx
from datetime import datetime, timedelta
import aiofiles
import uuid
from fastapi.concurrency import run_in_threadpool
from aiopath import AsyncPath

logger = logging.getLogger(__name__)


class ContentService(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
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
        self.content = remote_data.get("content")
        self.request = gateway.request
        self.local_settings = gateway.local_settings
        self.templates = gateway.templates
        self.session = gateway.session
        self.layout = None
        self.attachments_to_save = []
        self.component_filters = [
            {
                "id": "list_order",
                "input": "text",
                "label": "List Order",
                'default_operator': 'equal',
                "operators": ["equal", "not_equal", "greater", "greater_or_equal", "less", "less_or_equal", "in",
                              "not_in"],
                "type": "integer",
                "value_separator": "|"
            },
            {"id": "deleted", "label": "Eliminato",
             "operators": ["equal", "not_equal", "greater"],
             'default_operator': 'equal',
             "input": "text", "type": "integer"},
            {"id": "rec_name", "label": "Name", 'default_operator': 'contains', "type": "string"},
            {"id": "title", "label": "Title", 'default_operator': 'contains', "type": "string"},
            {"id": "type", "label": "Tipo", 'default_operator': 'contains', "type": "string"},
            {
                "id": "sys",
                "input": "radio",
                "label": "Di Sistema",
                "operators": ["equal", "is_null", "is_not_null"],
                "type": "boolean",
                "values": {0: "No", 1: "Yes"}
            }
        ]

    async def make_page(self):
        logger.info("Make Page")
        # get_layout
        # route form or table
        # add layout
        # render layout

        if self.content.get("builder") and self.content.get('mode') == "form":
            logger.info("FormIoBuilder")
            form_builder = FormIoBuilder.new(
                request=self.request, session=self.session,
                settings=self.session.get('app', {}).get("settings", self.local_settings),
                response=self.remote_data,
                templates=self.templates
            )
            content = await form_builder.form_builder()
            if self.request.query_params.get("iframe"):
                return content
        elif "cards" in self.content:
            logger.info(f"Make Page -> Dashboard")
            dashboard = DashboardWidget.new(
                templates_engine=self.templates, session=self.session,
                request=self.request, settings=self.session.get('app', {}).get("settings", self.local_settings),
                content=self.content.copy()
            )
            content = dashboard.make_dashboard()
            logger.info("Make Dashboard Done")
        else:
            logger.info(f"Make Page -> compute_{self.content.get('mode')}")
            content = await getattr(self, f"compute_{self.content.get('mode')}")()

        self.layout = await self.get_layout()
        # if not self.content.get("builder"):
        self.layout.make_context_button(self.content)
        self.layout.rows.append(content)
        logger.info("Make Page Done")
        return self.layout.render_layout()

    async def compute_list(self):
        logger.info("Compute Table List")
        return await self.render_table()

    async def eval_data_src_componentes(self, components_ext_data_src):
        if components_ext_data_src:
            for component in components_ext_data_src:
                if component.dataSrc in ["resource", "form"]:
                    component.resources = await self.gateway.get_ext_submission(
                        component.resource_id, params=component.properties.copy())
                elif component.dataSrc == "url":
                    logger.info(component)
                    logger.info(component.properties)

                    if component.idPath:
                        component.path_value = self.session.get(component.idPath, component.idPath)
                    if "http" not in component.url and "https" not in component.url:
                        url = f"{self.local_settings.service_url}{component.url}"
                        res = await self.gateway.get_remote_object(url, params=component.properties.copy())
                        component.resources = res.get("content", {}).get("data", {})[:]
                    else:
                        component.resources = await self.gateway.get_remote_data_select(
                            component.url, component.path_value, component.header_key, component.header_value_key
                        )
                    if component.selectValues and component.valueProperty:
                        if isinstance(component.resources, dict) and component.resources.get("result"):
                            tmp_res = component.resources.copy()
                            component.resources = []
                            component.resources = tmp_res['result'].get(component.selectValues)
                            component.selected_id = tmp_res['result'].get(component.valueProperty)
                    if component.valueProperty:
                        if "." in component.valueProperty:
                            to_eval = component.valueProperty.split(".")
                            obj = self.session.get(to_eval[0], {})
                            if obj and isinstance(obj, dict) and len(to_eval) > 1:
                                component.selected_id = obj.get(to_eval[1], "")
                        # logger.info(component.selected_id)
                    elif component.selectValues and isinstance(component.resources, dict):
                        component.resources = component.resources.get(component.selectValues)
                component.make_resource_list()

    async def create_folder(self, base_upload, model_data, sub_folder=""):
        form_upload = f"{base_upload}/{model_data}"
        if sub_folder:
            form_upload = f"{base_upload}/{model_data}/{sub_folder}"
        await AsyncPath(form_upload).mkdir(parents=True, exist_ok=True)
        return form_upload

    async def compute_form(self, modal=False):
        logger.info("Compute Form")

        page = FormIoWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request, settings=self.session.get('app', {}).get("settings", self.local_settings),
            content=self.content.copy(),
            schema=self.content.get('schema').copy(), modal=modal
        )

        await self.eval_data_src_componentes(page.components_ext_data_src)

        if page.tables:
            for table in page.tables:
                await self.eval_table(table, parent=page.rec_name)

        if page.search_areas:
            for search_area in page.search_areas:
                filters = await self.get_filters_for_model(search_area.model)
                query = await self.eval_search_area_query(search_area.model, search_area.query)
                search_area.query = query
                if search_area.model == "component":
                    search_area.filters = filters[:]
                else:
                    for c_filter in filters:
                        cfilter = c_filter.get_filter_object()
                        # logger.info(f"..form.filters. {cfilter}")
                        search_area.filters.append(cfilter)

        form = page.make_form()

        return form

    async def eval_datagrid_response(self, data_grid, render=False):
        results = {"rows": [], 'showAdd': data_grid.add_enabled}
        for row in data_grid.rows:
            if render:
                rendered_row = row.render(log=False)
                results['rows'].append(rendered_row)
            else:
                results['rows'].append(row)
        logger.info("eval_datagrid_response")
        return results

    async def compute_datagrid_rows(self, key):
        logger.info("compute_grid_rows")
        page = FormIoWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request, settings=self.session.get('app', {}).get("settings", self.local_settings),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        data_grid = page.grid_rows(key)
        await self.eval_data_src_componentes(data_grid.components_ext_data_src)
        if data_grid.tables:
            for table in data_grid.tables:
                await self.eval_table(table)

        res = await self.eval_datagrid_response(data_grid, render=True)

        return res

    async def compute_datagrid_add_row(self, key, num_rows):
        logger.info("compute_grid_add_row")

        page = FormIoWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request, settings=self.session.get('app', {}).get("settings", self.local_settings),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        data_grid = page.grid_add_row(key, num_rows)
        await self.eval_data_src_componentes(data_grid.components_ext_data_src)
        if data_grid.tables:
            for table in data_grid.tables:
                await self.eval_table(table)

        res = await self.eval_datagrid_response(data_grid, render=True)

        return res

    # TODO from html2docx import html2docx https://pypi.org/project/html2docx/
    async def print_form(self):
        logger.info("print_form")
        page = FormIoWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request, settings=self.session.get('app', {}).get("settings", self.local_settings),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        report_html = page.render_report_html()
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
        options = page.handle_header_footer(options)
        logger.info(options)
        pkit = pdfkit.PDFKit(report_html, 'string', options=options)
        await pkit.to_pdf(file_report)
        return FileResponse(file_report)

    async def fast_search_eval(self, data, field) -> list:
        logger.info("eval schema")

        page = FormIoWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request, settings=self.session.get('app', {}).get("settings", self.local_settings),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        await self.eval_data_src_componentes(page.components_ext_data_src)

        changed_components = page.form_compute_change_fast_search(data)

        await self.eval_data_src_componentes(page.components_change_ext_data_src)

        res = {"query": {}}
        for comp in changed_components:
            if comp.key == field:
                res['query'] = comp.properties.get("query", {})

        # resp = page.render_change_components(changed_components)
        logger.info(res)
        return await self.gateway.complete_json_response(res)

    # TODO fix see form_post
    async def form_change_handler(self, field) -> list:
        logger.info("Compute Form Change")
        submitted_data = await self.request.json()
        if "rec_name" in submitted_data and submitted_data.get("rec_name"):
            allowed = self.gateway.name_allowed.match(submitted_data.get("rec_name"))
            if not allowed:
                logger.error(f"name {submitted_data.get('rec_name')}")
                err = {
                    "status": "error",
                    "message": f"Errore nel campo name {submitted_data.get('rec_name')} caratteri non consentiti",
                    "model": submitted_data.get('data_model')
                }
                return await self.form_post_complete_response(err, None)
        page = FormIoWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request, settings=self.session.get('app', {}).get("settings", self.local_settings),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        await self.eval_data_src_componentes(page.components_ext_data_src)
        changed_components = page.form_compute_change(submitted_data)
        await self.eval_data_src_componentes(page.components_change_ext_data_src)
        if page.tables:
            for table in page.tables:
                await self.eval_table(table, parent=page.rec_name)

        if page.search_areas:
            for search_area in page.search_areas:
                filters = await self.get_filters_for_model(search_area.model)
                query = await self.eval_search_area_query(search_area.model, search_area.query)
                search_area.query = query
                if search_area.model == "component":
                    search_area.filters = filters[:]
                else:
                    for c_filter in filters:
                        cfilter = c_filter.get_filter_object()
                        # logger.info(f"..form.filters. {cfilter}")
                        search_area.filters.append(cfilter)

        resp = page.render_change_components(changed_components)

        return await self.gateway.complete_json_response(resp)

    async def form_post_handler(self, submitted_data) -> dict:
        logger.info(f"form_post_handler")
        page = FormIoWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request, settings=self.session.get('app', {}).get("settings", self.local_settings),
            content=self.content.copy(),
            schema=self.content.get('schema').copy()
        )
        await self.eval_data_src_componentes(page.components_ext_data_src)
        submit_data = await self.handle_attachment(
            page.uploaders, submitted_data.copy(), self.content.get("data", {}).copy())
        return page.form_compute_submit(submit_data)

    async def after_form_post_handler(self, remote_data, submitted_data, is_create=False):
        return remote_data.copy()

    async def form_post_complete_response(self, response_data, response):
        logger.info(f"form_post_complete_response")
        if "error" in response_data.get('status', ""):
            widget = WidgetsBase.create(templates_engine=self.templates, session=self.session, request=self.request)
            if self.gateway.session['app']['builder']:
                return widget.response_ajax_notices(
                    "error", f"builder_alert", response_data['message'])
            else:
                return widget.response_ajax_notices(
                    "error", f"{response_data['model']}_alert", response_data['message'])
        elif "action" in response_data and response_data.get("action") == "redirect":
            return self.gateway.complete_json_response({
                "link": response_data.get("url"),
                "reload": True
            })
        else:
            if self.attachments_to_save:
                for attachment in self.attachments_to_save:
                    await self.move_attachment(attachment)
            return await self.gateway.complete_json_response(response_data, orig_resp=response)

    async def get_layout(self, name="") -> LayoutWidget:
        logger.info(f"load layout {name}")
        logger.info(f"content breadcrumb: {self.remote_data.get('breadcrumb')}")
        url = f"{self.local_settings.service_url}/layout"
        if name:
            url = f"{url}?name={name}"
        schema_layout = await self.gateway.get_remote_object(
            url, headers={
                "referer": self.request.url.path
            }
        )
        layout = LayoutWidget.new(
            templates_engine=self.templates, session=self.session, request=self.request,
            settings=self.session.get('app', {}).get("settings", self.local_settings), content=schema_layout,
            schema=schema_layout.get('schema'), breadcrumb=self.remote_data.get('breadcrumb', [])
        )
        return layout

    async def eval_table(self, table, parent=""):
        table_content = await self.gateway.get_remote_object(
            f"{self.local_settings.service_url}{table.action_url}", params={"container_act": "y"}
        )
        table_config = TableWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.gateway.request, content=table_content.get('content'),
            disabled=False
        )
        table.columns = table_config.columns
        table.hide_rec_name = table_config.rec_name_is_meta
        table.meta_keys = table_config.columns_meta_list
        table.form_columns = table_config.form_columns
        table.parent = parent

    async def get_filters_for_model(self, model):
        logger.info(f"get_filters_for_model {model}")
        if not model == "component":
            server_response = await self.gateway.get_record(
                model, ""
            )
            content = server_response.get('content')
            # schema = content.get('schema')
            form = FormIoWidget.new(
                templates_engine=self.templates, session=self.session,
                request=self.request, settings=self.session.get('app', {}).get("settings", self.local_settings),
                content=content.copy(),
                schema=content.get('schema').copy()
            )
            await self.eval_data_src_componentes(form.components_ext_data_src)
            # logger.info(f"..form.filters. {form.filters}")
            return form.filters
        else:
            return self.component_filters

    async def eval_search_area_query(self, model, query_prop):
        logger.info("eval_search_area_query")
        params = self.gateway.request.query_params.__dict__['_dict'].copy()
        base_query = self.content.get("query", {})
        is_domain = self.content.get("is_domain_query", {})
        query = query_prop
        session_query = self.session.get('app')['queries'].get(model, {})
        if params.get('container_act') and session_query and not query_prop:
            query = session_query
        elif base_query and not is_domain and not query_prop:
            query = base_query
        return query

    async def render_table(self):
        logger.info("Render Table")
        # TODO prepare and Render Page -No Data-
        # table_view = '<div class="text-center"> <h4> No Data <h4> <div>'
        # if len(self.content.get('data')) > 0:
        widget = TableFormWidget.new(
            templates_engine=self.templates,
            session=self.gateway.session, request=self.gateway.request, content=self.content
        )

        if widget.tables:
            for table in widget.tables:
                await self.eval_table(table)

        if widget.search_areas:
            for search_area in widget.search_areas:
                filters = await self.get_filters_for_model(search_area.model)
                query = await self.eval_search_area_query(
                    search_area.model, search_area.query)
                search_area.query = query
                if search_area.model == "component":
                    search_area.filters = filters[:]
                else:
                    search_area.filters.append({"id": "deleted", "label": "Eliminato",
                                                "operators": ["equal", "not_equal", "greater"],
                                                "input": "text", "type": "integer"})
                    search_area.filters.append({"id": "active", "label": "Attivo",
                                                'values': {"true": 'Yes', "false": 'No'},
                                                "input": "radio", "type": "boolean"})
                    for c_filter in filters:
                        cfilter = c_filter.get_filter_object()
                        # logger.info(f"..form.filters. {cfilter}")
                        search_area.filters.append(cfilter)

        table_view = widget.render_widget()
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
        logger.info("process_data_table")
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
        response = await self.gateway.get_remote_object(
            "/clean/records", headers={}
        )
        return response

    async def polling_calendar_tasks(self):
        response = await self.gateway.get_remote_object(
            "/get/calendar_tasks", headers={}
        )
        return response

    async def execute_tasks(self, task_name):
        response = await self.gateway.post_remote_object(
            f"/run/calendar_tasks/{task_name}", headers={}
        )
        return response
