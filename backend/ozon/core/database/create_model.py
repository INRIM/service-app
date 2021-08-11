# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from typing import Any, Dict, Optional, List, Union, TypeVar, Generic

from odmantic import Model, EmbeddedModel
from pydantic import create_model
from pydantic.fields import ModelField
from datetime import datetime, date, time
import logging

logger = logging.getLogger(__name__)


class ModelMaker:
    def __init__(self, model_name: str, components: list):
        self.components = components[:]
        self.model_name = model_name
        self.unique_fields = ['rec_name']
        self.model = None
        self.no_create_model_field_key = [
            'tabs', 'columns', 'button', 'panel', 'form', 'fieldset',
            'resource', 'table', 'well', "htmlelement"]
        self.no_clone_field_type = ["file"]
        self.no_clone_field_keys = {}
        self.computed_fields = {}
        self.create_task_action = {}
        self.create_model_to_nesteded = ['datagrid']
        self.linked_object = []
        self.default_fields = {
            "rec_name": (str, ""),
            "parent": (str, ""),
            "childs": (List[Any], []),
            "process_id": (str, ""),
            "process_task_id": (str, ""),
            "type": (str, "form"),
            "data_value": (Dict, {}),
            "owner_name": (str, ""),
            "deleted": (float, 0),
            "list_order": (int, 0),
            "owner_uid": (str, ""),
            "owner_mail": (str, ""),
            "owner_function": (str, ""),
            "owner_function_type": (str, ""),
            "owner_sector": (str, ""),
            "owner_sector_id": (int, 0),
            "owner_personal_type": (str, ""),
            "owner_job_title": (str, ""),
            "update_uid": (str, ""),
            "create_datetime": (Optional[datetime], datetime.now()),
            "update_datetime": (Optional[datetime], datetime.now()),
            "sys": (bool, False),
            "default": (bool, False),
            "active": (bool, True),
            "demo": (bool, False)
        }
        self.mapper = {
            "textfield": [str, ""],
            "password": [str, ""],
            "file": [List[Dict], []],
            "email": [str, ""],
            "content": [str, ""],
            "textarea": [str, ""],
            "number": [int, 0],
            "number_f": [float, 0.0],
            "select": [str, ""],
            "select_multi": [List[str], []],
            "checkbox": [bool, False],
            "radio": [str, ""],
            "survey": [Dict, {}],
            "jsondata": [Dict, {}],
            "datetime": [Optional[datetime], datetime.now()],
            "datagrid": [List[Any], []],
        }
        self.make()

    def make_model(self, fields_def):
        self.model = create_model(self.model_name, __base__=Model, **fields_def)
        logger.info(f"Make model {self.model_name}... Done")

    def _scan(self, comp, dict_t):
        if comp.get("type") and comp.get("type") not in self.no_create_model_field_key:
            try:
                if comp.get("type") == "select" and comp.get("multiple"):
                    compo_todo = self.mapper.get("select_multi")[:]
                else:
                    if (
                            comp.get("type").lower() == "textarea" and
                            comp.get("properties", {}).get("type", "") == "json"
                    ):
                        compo_todo = self.mapper.get("jsondata")[:]
                    else:
                        compo_todo = self.mapper.get(comp.get("type"))[:]
            except Exception as e:
                logger.error(
                    f'Error creation model objec map: {comp.get("type")} {self.no_create_model_field_key} \n {e}')
            if comp.get("type") in self.no_clone_field_type:
                self.no_clone_field_keys.update({comp.get("key"): compo_todo[1]})
            if comp.get("defaultValue"):
                if type(comp.get("defaultValue")) == compo_todo[1]:
                    compo_todo[1] = comp.get("defaultValue")
            if comp.get("type") in self.create_model_to_nesteded:
                # print("Make Nested")
                dict_t[comp.get("key")] = (
                    List[
                        ModelMaker(comp.get("key"), comp.get("components")[:]).model
                    ], []
                )
                # print(dict_t)
            else:
                dict_t[comp.get("key")] = tuple(compo_todo)
                if comp.get("unique"):
                    self.unique_fields.append(comp.get("key"))
                    self.no_clone_field_keys.update({comp.get("key"): compo_todo[1]})
                if comp.get("calculateServer") and comp.get("calculateValue"):
                    self.computed_fields[comp.get("key")] = comp.get("calculateValue")
                    self.no_clone_field_keys.update({comp.get("key"): compo_todo[1]})
        if comp.get("type") == "fieldset" and comp.get("properties", {}).get("action_type"):
            gtype = comp.get("properties").get("type")
            self.create_task_action[comp.get("key")] = comp.get("properties")
        if comp.get("columns"):
            for col in comp.get("columns"):
                if col.get("components"):
                    for x in col.get("components"):
                        self._scan(x.copy(), dict_t)
        if comp.get("components"):
            for c in comp.get("components"):
                if c.get("colums"):
                    for col in c.get("columns"):
                        if col.get("components"):
                            for x in col.get("components"):
                                self._scan(x.copy(), dict_t)
                else:
                    self._scan(c.copy(), dict_t)
        return dict_t

    def make(self):
        dict_tx = {}
        dict_tt = {}
        for c in self.components:
            # print(c)
            dict_tx = self._scan(c, dict_tt)
        final = {**self.default_fields, **dict_tx}
        self.make_model(final)
