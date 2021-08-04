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

logger = logging.getLogger(__name__)


class TableFormWidget(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class TableFormWidgetBase(TableFormWidget, PageWidget):

    @classmethod
    def create(
            cls, templates_engine, session, request, content, disabled=False, **kwargs):
        self = TableFormWidgetBase()
        self.content = deepcopy(content)
        disabled = not self.content.get('editable')
        settings = content.get("settings")
        self.init(
            templates_engine, session, request, settings, disabled=disabled, **kwargs
        )
        self.model = self.content.get("model")
        self.action_url = self.content.get('action_url')
        self.action_name = self.content.get('action_name')
        self.orig_query = ujson.loads(self.session.get('queries').get(self.model, "{}"))
        self.show_owner_name = True
        self.schema = self.get_base_schema()
        self.builder = CustomBuilder(
            self.schema, template_engine=templates_engine,
            disabled=self.disabled, settings=settings, authtoken=self.authtoken,
            theme_cfg=self.theme_cfg, is_mobile=self.is_mobile
        )

        self.components_ext_data_src = self.builder.components_ext_data_src
        self.tables = self.builder.tables
        self.search_areas = self.builder.search_areas
        self.filters = self.builder.filters
        return self

    def get_base_schema(self):
        return {
            "title": self.content.get('title'),
            "customClass": "text-center col-12",
            "key": self.model,
            "type": "container",
            "components": [
                {
                    "label": "Columns",
                    "columns": [
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
                            "width": 6,
                            "offset": 0,
                            "push": 0,
                            "pull": 0,
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
                                        "model": self.model,
                                        "query": self.orig_query,
                                    },
                                    "type": "well",
                                    "input": False,
                                    "tableView": False,
                                    "components": []
                                },
                            ],
                            "width": 6,
                            "offset": 0,
                            "push": 0,
                            "pull": 0,
                            "size": "md"
                        }
                    ],
                    "key": "columns",
                    "type": "columns",
                    "input": False,
                    "tableView": False
                },
                {
                    "label": "Table",
                    "cellAlignment": "left",
                    "key": f'{self.model}_{self.action_name}',
                    "properties": {
                        "action_name": self.action_name,
                        "action_url": self.action_url,
                        "model": self.model,
                        "show_owner": "no",
                        "hide_select_chk": 'no',
                        "list_metadata_show": "list_order",
                        "dom": "iptilp"
                    },
                    "type": "table",
                    "customClass": "table table-borderless p-2",
                    "input": False,
                    "tableView": False,
                    "rows": []
                }
            ]
        }.copy()

    def render_widget(self):
        return self.builder.main.render(log=False)
