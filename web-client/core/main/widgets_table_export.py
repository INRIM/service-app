# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import collections
import sys
from copy import deepcopy
import logging
import ujson
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from datetime import datetime, timedelta
from .builder_custom import *
from . import custom_components
from .widgets_content import PageWidget
from .base.base_class import BaseClass, PluginBase
from io import BytesIO
from collections import OrderedDict

# import xlsxwriter
import pandas as pd

logger = logging.getLogger(__name__)


class TableWidgetExport(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        if cls not in cls.plugins:
            cls.plugins.append(cls())


class TableWidgetExportBase(TableWidgetExport, PageWidget):
    # TODO Fix export area using current action name to handle view type
    @classmethod
    def create(
        cls,
        templates_engine,
        session,
        request,
        settings,
        content,
        file_type="json",
        **kwargs,
    ):
        self = TableWidgetExportBase()
        self.settings = deepcopy(settings)
        self.init(
            templates_engine,
            session,
            request,
            settings,
            disabled=False,
            **kwargs,
        )
        self.content = deepcopy(content)
        logger.debug(self.content)
        self.model = self.content.get("model")
        self.schema = self.content.get("schema")
        self.data = self.content.get("data")
        self.builder = CustomBuilder(
            self.schema,
            template_engine=templates_engine,
            disabled=self.disabled,
            settings=settings,
            authtoken=self.authtoken,
            theme_cfg=self.theme_cfg,
            is_mobile=self.is_mobile,
            security_headers=self.security_headers,
        )
        logger.info("make_def_table_export")
        # TODO Handle i18n
        # self.form_c = CustomForm({}, self.builder)
        self.file_type = file_type
        return self

    def get_default_cols(self):
        return {
            "owner_uid": "ID Utente",
            "owner_name": "Utente",
            "owner_sector": "Utente Div/Uo",
            "owner_function": "Utente Funz",
            "owner_personal_type": "Tipo Personale",
            "owner_job_title": "Qualifica",
            "update_uid": "Utente Aggiornamento",
            "update_datetime": "Data Aggionamento",
            "create_datetime": "Data Creazione",
        }

    def get_columns(self):
        logger.info(f" get_columns")
        cols = {"list_order": "O"}
        for key, component in self.builder.components.items():
            if (
                key
                and component
                and not component.survey
                and not component.multi_row
                and component.type not in self.builder.layout_obj_types
            ):
                cols[key] = component.label
        def_cols = self.get_default_cols()
        res_cols = {**cols, **def_cols}
        return collections.OrderedDict(res_cols.copy())

    async def export_data(self):
        return await getattr(self, f"export_{self.file_type}")()

    async def export_json(self):
        logger.info("Export Json")
        dt_report = datetime.now().strftime(
            self.settings["server_datetime_mask"]
        )
        file_name = f"{self.model}_{dt_report}.json"
        output = BytesIO()
        data = ujson.dumps(
            self.data, escape_forward_slashes=False, ensure_ascii=False
        )
        output.write(data.encode("utf-8"))
        output.seek(0)
        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"',
        }
        logger.info(f"Make Export file Done: {file_name}")
        return StreamingResponse(
            output, headers=headers, media_type="text/plain"
        )

    async def export_xls(self, raw=False):
        logger.info("Export Xls")
        dt_report = datetime.now().strftime(
            self.settings["server_datetime_mask"]
        )
        file_name = f"{self.model}_{dt_report}.xlsx"
        # keys_row = self.data[0].keys()
        columns = self.get_columns()
        list_key = list(columns.keys())
        data = copy.deepcopy(self.data)
        if not raw:
            for idx, item in enumerate(self.data):
                data_values = item.get("data_value")
                for k in list_key:
                    if (
                        k in data[idx]
                        and type(data[idx][k]) in [list, str, datetime]
                        and k in data_values
                    ):
                        data[idx][k] = data_values[k]
        df = pd.DataFrame(data, columns=list_key)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer) as writer:
            df.to_excel(writer, header=list(columns.values()), index=False)
        buffer.seek(0)

        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"'
        }
        return StreamingResponse(buffer, headers=headers)

    async def export_csv(self, raw=False):
        logger.info("Export Csv")
        dt_report = datetime.now().strftime(
            self.settings["server_datetime_mask"]
        )
        file_name = f"{self.model}_{dt_report}.csv"
        keys_row = self.data[0].keys()
        columns = self.get_columns()
        list_key = list(columns.keys())
        buffer = BytesIO()
        data = copy.deepcopy(self.data)
        if not raw:
            for idx, item in enumerate(self.data):
                data_values = item.get("data_value")
                for k in list_key:
                    if (
                        k in data[idx]
                        and type(data[idx][k]) in [list, str, datetime]
                        and k in data_values
                    ):
                        data[idx][k] = data_values[k]
        df = pd.DataFrame(data, columns=list_key)
        # df.columns = list(columns.values())
        df = df.rename(columns=columns)
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"'
        }
        return StreamingResponse(buffer, headers=headers)
