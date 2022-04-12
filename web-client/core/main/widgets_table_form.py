# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import collections
import sys
from copy import deepcopy
import logging
import ujson
from fastapi.templating import Jinja2Templates

from .builder_custom import *
from .widgets_content import PageWidget
from .base.base_class import BaseClass, PluginBase
from datetime import datetime, date

logger = logging.getLogger(__name__)


class TableFormWidget(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        if cls not in cls.plugins:
            cls.plugins.append(cls())


class TableFormWidgetBase(TableFormWidget, PageWidget):

    @classmethod
    def create(
            cls, templates_engine, session, request, content, disabled=False, **kwargs):
        self = TableFormWidgetBase()
        self.content = deepcopy(content)
        disabled = not self.content.get('editable')
        sett = session.get('app')['settings'].copy()
        self.init(
            templates_engine=templates_engine, session=session, request=request,
            settings=sett, disabled=disabled, **kwargs
        )
        self.model = self.content.get("model")
        self.schema_form = self.content.get("schema")
        self.action_url = self.content.get('action_url')
        self.action_name = self.content.get('action_name')
        self.fast_search_cfg = self.content.get('fast_search', {})
        self.fast_search_model = self.fast_search_cfg.get("fast_serch_model", {})
        self.fast_search_schema = self.fast_search_cfg.get("schema", {})
        self.fast_search_components = self.fast_search_schema.get("components", [])
        self.order = self.content.get('sort', 'list_order:asc,rec_name:desc')
        self.orig_query = {}
        self.show_owner_name = True
        self.export_model = self.content.get("model")
        schema_data_model = self.schema_form.get("data_model")
        if schema_data_model and not schema_data_model == "no_model":
            self.export_model = self.schema_form.get("rec_name")
        self.schema = self.get_base_schema(self.fast_search_components)
        self.context_data = session.copy()
        if "app" not in self.context_data:
            self.context_data['app'] = {}
        self.context_data['app']["year"] = date.today().year
        self.context_data['app']["month"] = date.today().month
        self.context_data['form'] = content.get("data", {})
        return self

    # TODO handle specific form e config for this kind data
    def get_base_schema(self, fast_search=[]):
        std_component = []
        tools = [
            {
                "components": [
                    {
                        "label": "Search Area",
                        "customClass": "col-12",
                        "key": "search_area",
                        "properties": {
                            "type": "search_area",
                            "object_id": f'{self.model}_{self.action_name}',
                            "model": self.model,
                            "query": self.orig_query,
                            "object": 'table'
                        },
                        "type": "well",
                        "input": False,
                        "tableView": False,
                        "components": []
                    },
                ],
                "width": 3,
                "offset": 0,
                "push": 0,
                "pull": 0,
                "customClass": "ozon-col-auto",
                "size": "md"
            },
            {
                "components": [
                    {
                        "label": "Export Area",
                        "customClass": "col-12",
                        "key": "export_area",
                        "properties": {
                            "type": "export_area",
                            "search_id": f'search_area',
                            "model": self.export_model,
                            "query": self.orig_query,
                        },
                        "type": "well",
                        "input": False,
                        "tableView": False,
                        "components": []
                    },
                ],
                "width": 3,
                "offset": 0,
                "push": 0,
                "pull": 0,
                "customClass": "ozon-col-auto",
                "size": "md"
            }
        ]
        if self.is_admin:
            tools.append(
                {
                    "components": [
                        {
                            "label": "Import",
                            "customClass": "col-3",
                            "key": "import_component",
                            "properties": {
                                "type": "import_component",
                                "title": "Import Data",
                                "model": self.model
                            },
                            "type": "well",
                            "input": False,
                            "tableView": False,
                            "components": []
                        },
                    ],
                    "width": 3,
                    "offset": 0,
                    "push": 0,
                    "pull": 0,
                    "customClass": "ozon-col-auto",
                    "size": "md"
                }
            )
        std_component.append({
            "label": "Columns",
            "columns": tools,
            "key": "columns",
            "type": "columns",
            "input": False,
            "tableView": False
        })
        std_component.append({
            "label": "Table",
            "cellAlignment": "left",
            "key": f'{self.model}_{self.action_name}',
            "properties": {
                "action_name": self.action_name,
                "action_url": self.action_url,
                "model": self.model,
                "order": self.order,
                "show_owner": "no",
                "hide_select_chk": 'no',
                "list_metadata_show": "list_order",
                "dom": "iptilp"
            },
            "type": "table",
            "customClass": "table table-sm table-borderless table-striped table-hover",
            "input": False,
            "tableView": False,
            "rows": []
        })
        components = fast_search[:] + std_component
        return {
            "title": self.content.get('title'),
            "customClass": "text-center col-12",
            "key": self.model,
            "type": "container",
            "components": components
        }.copy()

    def init_table(self, data={}):
        logger.debug("init table")
        self.builder = CustomBuilder(
            self.schema, template_engine=self.tmpe,
            disabled=self.disabled, settings=self.settings, authtoken=self.authtoken,
            theme_cfg=self.theme_cfg, is_mobile=self.is_mobile, context=self.context_data.copy(),
            security_headers=self.security_headers, form_data=data.copy()
        )

        self.components_ext_data_src = self.builder.components_ext_data_src
        self.tables = self.builder.tables
        self.search_areas = self.builder.search_areas
        self.filters = self.builder.filters

    def render_widget(self):
        return self.builder.main.render(log=False)
