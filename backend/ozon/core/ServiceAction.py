# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
import os
from os import listdir
from os.path import isfile, join
import ujson
import json
from ozon.settings import get_settings
from .database.mongo_core import *
from collections import OrderedDict
from pathlib import Path
from fastapi import Request
from .ServiceSecurity import ServiceSecurity
from .ServiceMenuManager import ServiceMenuManager
from .ModelData import ModelData
from .BaseClass import BaseClass, PluginBase
from pydantic import ValidationError
from .QueryEngine import QueryEngine, DateTimeEncoder
from fastapi.encoders import jsonable_encoder

import logging
import pymongo
import requests
import httpx
import re
from urllib.parse import quote
from fastapi_cache.decorator import cache

logger = logging.getLogger(__name__)


class ServiceAction(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class ActionMain(ServiceAction):

    @classmethod
    def create(
            cls, session: Session, service_main, action_name, rec_name, parent, iframe, execute, pwd_context,
            container_act=""):
        self = ActionMain()
        self.init(session, service_main, action_name, rec_name, parent, iframe, execute, pwd_context,
                  container_act=container_act)
        return self

    def init(
            self, session: Session, service_main, action_name, rec_name, parent, iframe, execute, pwd_context,
            container_act=""):
        self.action_name = action_name
        self.session = session
        self.service_main = service_main
        self.curr_ref = rec_name
        self.data_model = None
        self.container_action = container_act
        self.action_model = None
        self.component_type = ""
        self.action_query = {}
        self.models_query = {}
        self.data_model_query = {}
        self.parent = parent
        self.iframe = iframe
        self.execute = execute
        self.computed_fields = {}
        self.model = None
        self.record = None
        self.action = None
        self.next_action = None
        self.ref_name = ""
        self.ref = ""
        self.contextual_actions = []
        self.contextual_buttons = []
        self.name_allowed = re.compile(r"^[A-Za-z0-9._~()'!*:@,;+?-]*$")
        self.sort_dir = {
            "asc": 1,
            "desc": -1
        }
        self.app_code = self.service_main.app_code
        self.defautl_sort_string = "list_order:asc,rec_name:desc"
        self.mdata = ModelData.new(session=session, pwd_context=pwd_context, app_code=self.app_code)
        self.menu_manager = ServiceMenuManager.new(session=session, app_code=self.app_code)
        self.acl = ServiceSecurity.new(session=session, app_code=self.app_code)
        self.qe = QueryEngine.new(session=session, app_code=self.app_code)
        # self.settings = self.mdata.app_settings
        self.fast_search_model = False
        self.fast_search = {}
        self.fast_config = {}

    @cache(expire=600)
    async def make_settings(self):
        self.app_settings = await self.mdata.get_app_settings(app_code=self.app_code)

    async def get_param(self, name: str) -> Any:
        return await get_param(name)

    # helper
    async def get_builder_config(self):
        if self.action.builder_enabled and self.mode == "component" and self.action.mode == "form":
            return {"page_api_action": f"/action/{component_type}/formio_builder/"}
        else:
            return {}

    async def eval_context_button_query(self):
        builder_active = self.action.builder_enabled
        user_query = await self.acl.make_user_action_query()
        pre_list = [
            {"model": {"$eq": self.action.model}},
            {
                "context_button_mode":
                    {"$elemMatch": {"$eq": self.action.mode}}
            },
            {"builder_enabled": {"$eq": self.action.builder_enabled}},
        ]
        if user_query:
            and_list = pre_list + user_query
        else:
            and_list = pre_list[:]
        if self.action.component_type:
            and_list.append(
                {"component_type": {"$eq": self.action.component_type}},
            )
        rel_name = self.aval_related_name()
        if builder_active:
            if rel_name:
                and_list.append(
                    {"ref": {"$exists": True, "$ne": ""}},
                )
            else:
                if self.action.mode == "list":
                    and_list.append(
                        {"ref": {"$in": ["", "self"]}},
                    )
                else:
                    and_list.append(
                        {"ref": {"$in": [""]}},
                    )

        query = {
            "$and": and_list
        }
        return query.copy()

    async def make_context_button(self):
        logger.debug(f"make_context_button object model: {self.action_model}")
        if self.action.model:
            query = self.qe.default_query(self.action_model, await self.eval_context_button_query())
            self.contextual_actions = await self.mdata.get_list_base(
                self.action_model, query=query)

            self.contextual_buttons = await self.menu_manager.make_action_buttons(
                self.contextual_actions, rec_name=self.curr_ref)
        # else:
        #     self.contextual_buttons = await self.menu_manager.make_main_menu()
        logger.debug(
            f"Done make_context_button  object model: {self.action_model} of {len(self.contextual_buttons)} items")

    async def eval_editable(self, model_schema, data):
        can_edit = False
        if isinstance(data, BasicModel):
            can_edit = await self.acl.can_update(model_schema, data)
        elif isinstance(data, list):
            can_edit = not self.session.is_public
        logger.info(can_edit)
        return can_edit

    async def eval_editable_fields(self, model_schema, data):
        fields = []
        if isinstance(data, BasicModel):
            fields = await self.acl.can_update_fields(model_schema, data)
        logger.info(fields)
        return fields

    async def eval_editable_and_context_button(self, model_schema, data):
        can_edit = await self.eval_editable(model_schema, data)
        if can_edit:
            await self.make_context_button()
        return can_edit

    def aval_related_name(self):
        related_name = self.curr_ref
        if not self.action.ref == "self" and not related_name:
            related_name = str(self.action.ref)
        logger.info(f"{self.curr_ref}, action.ref: {self.action.ref} ->  {related_name} ")

        return related_name

    def eval_sort_str(self, sortstr):
        sort_rules = sortstr.split(",")
        sort = []
        for rule_str in sort_rules:
            rule_list = rule_str.split(":")
            rule = (rule_list[0], self.sort_dir[rule_list[1]])
            sort.append(rule)
        return sort

    def eval_sorting(self, data):
        sortstr = data.get("sort")
        if not sortstr:
            sortstr = self.defautl_sort_string
        return self.eval_sort_str(sortstr)

    def eval_next_related_name(self, related_name):
        if self.action.action_type in ["save", "copy", "delete"]:
            if self.next_action and not self.next_action.ref == "self":
                related_name = str(self.next_action.ref)
        return related_name

    async def compute_action_path(self, record, related_name=""):
        act_path = f"{self.action.action_root_path}/{self.action.rec_name}"
        if self.next_action:
            act_path = f"{self.next_action.action_root_path}/{self.next_action.rec_name}"
        if self.action.ref:
            if self.action.ref == "self":
                if record:
                    act_path = f"{act_path}/{record.rec_name}"
            else:
                act_path = f"{act_path}/{self.action.ref}"

        if self.action.parent and not self.action.ref:
            if self.action.parent == "self":
                if record:
                    act_path = f"{act_path}/{record.parent}"
            else:
                act_path = f"{act_path}/{self.action.parent}"

        if self.action.keep_filter:
            act_path = f"{act_path}?container_act=y"
        return act_path

    def eval_builder_active(self, related_name=""):
        logger.info("eval_builder_active")
        builder = self.action.builder_enabled
        if self.action.mode == "form" and self.action.type == "data":
            builder = False
        return builder

    def prepare_list_query(self, data, data_model_name):
        q = {}
        if not self.action.action_type == "menu" or not self.container_action == "s":
            sess_query = self.session.app.get('queries').get(data_model_name)
        else:
            self.session.app.get('queries')[data_model_name] = {}
            sess_query = {}
        list_query = {}
        if self.action.list_query:
            list_query = ujson.loads(self.action.list_query)
        session_q = {}
        if self.container_action and sess_query:
            session_q = ujson.loads(sess_query)
        q = {**session_q, **list_query}

        if data.get("query") and not data.get("query") == "clean":
            data_q = data.get("query")
            if isinstance(data_q, dict) or isinstance(data, list):
                parsed_q = data_q
            elif isinstance(data_q, str):
                parsed_q = self.qe.check_parse_json(data_q)
            query = {**q, **parsed_q}
        else:
            query = q
        return query.copy()

    async def eval_computed_fields(self, data={}, eval_todo=True):
        logger.info(f"{self.computed_fields}")
        for k, v in self.computed_fields.items():
            if hasattr(self, v):
                mtd = getattr(self, v)
                if v == "eval_data":
                    data = await mtd(data, eval_todo=eval_todo)
                if v == "eval_user_todo":
                    data = await mtd(data, eval_todo=eval_todo)
                else:
                    data = await mtd(data)
        return data

    async def eval_data(self, data={}, eval_todo=True):
        return data.copy()

    # actions
    async def compute_action(self, data: dict = {}) -> dict:
        logger.info(f"compute_action action name -> act_name:{self.action_name}, data keys:{data.keys()}")
        self.fast_search_model = await self.mdata.gen_model('fast_search_config')
        self.action_model = await self.mdata.gen_model("action")
        self.action = await self.mdata.by_name(self.action_model, self.action_name)
        if not self.action:
            logger.error(f"No action found forn act_name: {self.action_name} model: {self.action_model}")
        if not self.action or self.action.admin and self.session.is_public:
            return {
                "action": "redirect",
                "url": "/login/",
            }
        can_read = await self.acl.can_read(self.action)
        if not can_read:
            return {
                "action": "redirect",
                "url": "/",
            }
        self.model = self.action.model
        self.next_action = await self.mdata.by_name(self.action_model, self.action.next_action_name)
        logger.info(f"Call method -> {self.action.action_type}_action")
        logger.info(f"Next action -> {self.action.next_action_name}")
        try:
            res = await getattr(self, f"{self.action.action_type}_action")(data=data)
            return res
        except ValidationError as e:
            logger.error(str(e))
            logger.error(f"data: {data}")
            return {
                "status": "error",
                "model": self.model,
                "message": str(e)
            }
        except RuntimeError as e:
            return {
                "status": "error",
                "model": self.model,
                "message": str(e)
            }

    async def eval_list_mode(self, related_name, data_model_name, data={}):
        logger.info(
            f"eval_list_mode action_model: {self.action.model}, data_model: {self.data_model},"
            f" component_type: {self.component_type}, related_name: {related_name}, data:{data}"
            f" data_model_name: {data_model_name}, container_act: {self.container_action}"
        )
        await self.make_context_button()

        action_url = f"{self.action.action_root_path}/{self.action.rec_name}"
        logger.info(f"List context Actions  {len(self.contextual_buttons)}")
        act_path = await self.compute_action_path(False)

        fields = []
        list_data = []
        merge_field = ""
        schema_sort = {}
        can_edit = False

        if self.action.model == "component" and self.data_model == Component and not related_name:
            model_schema = await self.mdata.component_by_type(self.component_type)
            if model_schema:
                schema = await self.mdata.component_by_name(model_schema[0].rec_name)
                fields = ["row_action", "title", "type", "display"]
            else:
                schema = {}
        else:
            # ????
            if self.action.model == "component" and related_name and self.component_type:
                schema = await self.mdata.component_by_name(related_name)
            else:
                # fast_search = await self.mdata
                logger.info(self.action.model)
                model_schema = await self.mdata.component_by_name(self.action.model)
                schema = model_schema
                schema_sort = schema.properties.get("sort")

        if not data.get("sort") and schema_sort:
            data['sort'] = schema.properties.get("sort")
        sortstr = data.get("sort")

        if not sortstr:
            sortstr = self.defautl_sort_string
        sort = self.eval_sort_str(sortstr)
        limit = data.get("limit", 0)
        skip = data.get("skip", 0)

        query = self.prepare_list_query(data, data_model_name)

        query = self.qe.default_query(
            self.data_model, query, parent=self.action.parent, model_type=self.component_type)

        self.session.app.get('queries')[data_model_name] = json.dumps(query, cls=DateTimeEncoder)

        if self.container_action:
            action_url = f"{action_url}?container_act=y"
            self.session.app['breadcrumb'][action_url] = self.action.title
        else:
            self.session.app['breadcrumb'] = {}
        if self.execute:
            list_data = await self.mdata.get_list_base(
                self.data_model, fields=fields,
                query=query, sort=sort, limit=limit, skip=skip,
                model_type=self.component_type, parent=related_name,
                row_action=act_path, merge_field=merge_field)

        recordsTotal = await self.mdata.count_by_filter(self.data_model, query=query)

        can_edit = await self.eval_editable_and_context_button(schema, list_data)

        self.session.app['action_name'] = self.action.rec_name
        self.session.app['curr_model'] = self.action.model
        self.session.app['curr_schema'] = schema
        self.session.app['builder'] = self.action.builder_enabled
        self.session.app['component_type'] = self.component_type

        return {
            "editable": can_edit,
            "context_buttons": self.contextual_buttons[:],
            "mode": self.action.mode,
            "query": query,
            "is_domain_query": self.action.force_domain_query,
            "limit": limit,
            "skip": skip,
            "sort": sortstr,
            "recordsTotal": recordsTotal,
            "recordsFiltered": recordsTotal,
            "data": list_data[:],
            "schema": schema,
            "action_url": action_url,
            "action_name": self.action.rec_name,
            "related_name": related_name,
            "builder": self.action.builder_enabled,
            "component_type": self.component_type,
            "model": self.action.model,
            "title": self.action.title,
            "fast_search": self.fast_config.copy()
        }

    async def eval_form_mode(self, related_name, data_model_name, data={}):
        builder_active = self.eval_builder_active()
        logger.info(
            f"eval_form_mode Name:{self.action.rec_name},  Model:{self.action.model}, Data Model: {self.data_model},"
            f"action_type:{self.action.type}, action_name: {self.action_name}, related: {self.curr_ref}, "
            f"default: {self.action.ref}, related_name: {related_name}, builder: {builder_active}"
        )
        fields = []
        if self.action.model == "component":
            if not self.action_model == self.data_model:
                model_schema = await self.mdata.component_by_name(self.curr_ref)
            else:
                model_schema = await self.mdata.component_by_name(related_name)
        else:
            model_schema = await self.mdata.component_by_name(self.action.model)

        data = {}
        if self.data_model:
            data = await self.mdata.by_name(
                self.data_model, record_name=related_name)

        if related_name:
            can_edit = await self.eval_editable_and_context_button(model_schema, data)
            fields = await self.eval_editable_fields(model_schema, data)
        else:
            can_edit = await self.eval_editable_and_context_button(model_schema, self.data_model(**{}))
            fields = await self.eval_editable_fields(model_schema, self.data_model(**{}))

        action_url = await self.compute_action_path(data)

        if not self.parent:
            self.session.app['mode'] = self.action.mode
            self.session.app['curr_model'] = self.action.model
            self.session.app['curr_schema'] = model_schema
            self.session.app['curr_data'] = data
            self.session.app['builder'] = builder_active
            self.session.app['component_type'] = self.component_type
            self.session.app['child'] = []
        else:
            self.session.app[self.action.rec_name] = {}
            self.session.app['child'].append(self.action.rec_name)
            self.session.app[self.action.rec_name]['mode'] = self.action.mode
            self.session.app[self.action.rec_name]['curr_model'] = self.action.model
            self.session.app[self.action.rec_name]['curr_schema'] = model_schema
            self.session.app[self.action.rec_name]['curr_data'] = data
            self.session.app[self.action.rec_name]['builder'] = builder_active
            self.session.app[self.action.rec_name]['component_type'] = self.component_type

        res = {
            "editable": can_edit,
            "editable_fields": fields,
            "context_buttons": self.contextual_buttons[:],
            "action_name": self.action.rec_name,
            "mode": self.action.mode,
            "schema": jsonable_encoder(model_schema),
            "data": jsonable_encoder(data),
            "builder": builder_active,
            "component_type": self.component_type,
            "model": self.action.model,
            "title": self.action.title,
            "action_url": action_url,
            "rec_name": related_name
        }

        if self.action.builder_enabled and not self.iframe:
            builder_action = f"{self.action.action_root_path}/{self.action_name}"
            if self.curr_ref:
                builder_action = f"{builder_action}/{self.curr_ref}"
            res["builder_api_action"] = builder_action
        return res.copy()

    async def window_action(self, data={}):
        logger.info(
            f"window_action -> {self.action.model}, action_type {self.action.type},"
            f" component_type: {self.action.component_type}, mode: {self.action.mode}"
        )
        related_name = self.aval_related_name()

        if self.action.type == "component":
            # get Schema
            logger.debug(f'Make Model Component: -> {self.action.model} | action type Component: -> {self.action.type}')
            self.data_model = await self.mdata.gen_model(self.action.type)
            data_model_name = self.action.type
            self.component_type = self.action.component_type
        else:
            # get Data
            if self.action.model == "component" and related_name:
                # list component -> row componet type -> list data of compenent
                logger.info(f'Make Model Component: -> {self.action.model} action type: -> {self.action.type}')
                self.data_model = await self.mdata.gen_model(related_name)
                self.component_type = self.action.component_type
                data_model_name = related_name
                related_name = ""
            else:
                logger.info(f'Make Model no component_type: -> {self.action.model} action type: -> {self.action.type}')
                self.data_model = await self.mdata.gen_model(self.action.model)
                data_model_name = self.action.model
                self.component_type = ""

        logger.info(f'Data Model: -> {self.data_model}')

        return await getattr(self, f"eval_{self.action.mode}_mode")(related_name, data_model_name, data=data)

    async def menu_action(self, data={}):
        logger.info(f"menu_action -> {self.action.model} action_type {self.action.type}")
        related_name = self.aval_related_name()
        query = {"$and": [{"model": self.action.rec_name}, {"deleted": 0}]}
        list_fast_search = await self.mdata.search_base(
            self.fast_search_model, query, sort=[], limit=0, skip=0
        )
        if list_fast_search:
            data_fast_search = list_fast_search[0]
            form_fast_search = data_fast_search.searchForm
            if form_fast_search:
                form_search_schema = await self.mdata.component_by_name(form_fast_search)
                self.fast_config = {
                    "model": self.action.model,
                    "schema": form_search_schema,
                    "fast_serch_model": form_fast_search,
                    "data": {},
                }
        if self.action.type == "component":
            self.data_model = await self.mdata.gen_model(self.action.type)
            self.component_type = self.action.component_type
            data_model_name = self.action.type
        else:
            self.data_model = await self.mdata.gen_model(self.action.model)
            self.component_type = ""
            data_model_name = self.action.model

        return await getattr(self, f"eval_{self.action.mode}_mode")(related_name, data_model_name, data=data)

    def make_error_message(self, message):
        return {
            "status": "error",
            "message": message,
            "model": self.action.model
        }

    async def save_copy_component(self, data={}, copy=False):
        logger.info(f"save_copy_component -> {self.action.model} action_type {self.action.type}")
        self.data_model = await self.mdata.gen_model(self.action.model)
        to_save = self.data_model(**data)
        record = await self.mdata.save_object(
            self.session, to_save, rec_name=self.curr_ref, model_name="component", copy=copy)
        return record

    async def before_save(self, record, rec_name="", model_name="", copy=False):
        return record

    async def after_save(self, record, rec_name="", model_name="", copy=False):
        return record

    async def save_copy(self, data={}, copy=False, eval_todo=True):
        logger.info(f"save_copy -> {self.action.model} action_type: {self.action.type}")
        self.data_model = await self.mdata.gen_model(self.action.model)
        self.computed_fields = self.mdata.computed_fields
        if self.computed_fields:
            data = await self.eval_computed_fields(data, eval_todo=eval_todo)
        if copy:
            data = self.mdata.clean_data_to_clone(data)
        to_save = self.data_model(**data)
        if not self.curr_ref and not to_save.rec_name:
            to_save.rec_name = f"{self.action.model}.{to_save.id}"
        elif self.curr_ref and not to_save.rec_name:
            to_save.rec_name = self.curr_ref
        if not self.name_allowed.match(to_save.rec_name):
            logger.error(f"Errore nel campo name {to_save.rec_name}")
            return self.make_error_message(f"Errore nel campo name {to_save.rec_name} caratteri non consentiti")

        to_save = await self.before_save(
            record=to_save, rec_name=self.curr_ref, model_name=self.action.model, copy=copy)

        if isinstance(to_save, dict):
            return to_save

        record = await self.mdata.save_object(
            self.session, to_save, rec_name=self.curr_ref, model_name=self.action.model, copy=copy)
        record = await self.after_save(
            record=record, rec_name=self.curr_ref, model_name=self.action.model, copy=copy)
        return record

    async def check_and_create_task_action(self, record):
        await self.mdata.gen_model(record.rec_name)
        logger.info(self.mdata.create_task_action)
        if self.mdata.create_task_action:
            for k, config in self.mdata.create_task_action.items():
                actions = await self.mdata.count_by_filter(
                    self.action_model, {
                        "$and": [
                            {"model": record.rec_name},
                            {"rec_name": f"{record.rec_name}_{config['rec_name']}"}
                        ]})
                if actions == 0:
                    await self.mdata.make_action_task_for_model(
                        self.session, record.rec_name, record, config.copy())

    async def save_action(self, data={}):
        logger.info(
            f"save_action -> model:{self.action.model} action_type:{self.action.type}, curr_ref:{self.curr_ref}")
        # related_name = self.aval_related_name()
        reload = True
        model_schema = False
        if self.action.model == "component":
            record = await self.save_copy_component(data=data)
            actions = await self.mdata.count_by_filter(self.action_model, {"$and": [{"model": record.rec_name}]})
            if (
                    not isinstance(record, dict) and
                    record.type in ['form', 'resource'] and
                    self.action.builder_enabled and
                    actions == 0 and not record.data_model
            ):
                logger.info("make auto actions for model")
                await self.mdata.make_default_action_model(
                    self.session, record.rec_name, record)

            await self.check_and_create_task_action(record)
        else:
            model_schema = await self.mdata.component_by_name(self.action.model)
            if not model_schema.data_model == "no_model":
                record = await self.save_copy(data=data)
            else:
                reload = False
                data_model = await self.mdata.gen_model(self.action.model)
                objectd = data_model(**data)
                record = await self.before_save(
                    record=objectd, rec_name=self.curr_ref, model_name=self.action.model)
        # if is error record is dict
        if isinstance(record, dict):
            return record

        act_path = await self.compute_action_path(record)
        self.session.app['curr_data'] = record.get_dict()
        return {
            "status": "ok",
            "link": f"{act_path}",
            "reload": reload,
            "schema": model_schema.get_dict() if model_schema else {},
            "data": record.get_dict()
        }

    async def copy_action(self, data={}):
        logger.info(
            f"copy_action -> model:{self.action.model} action_type:{self.action.type}, curr_ref:{self.curr_ref}")
        related_name = self.aval_related_name()
        if self.action.model == "component":
            model_schema = {}
            record = await self.save_copy_component(data=data, copy=True)
            actions = await self.mdata.count_by_filter(self.action_model, {"$and": [{"model": record.rec_name}]})
            if (
                    not isinstance(record, dict) and
                    record.type in ['form', 'resource'] and
                    self.action.builder_enabled and
                    actions == 0 and not record.data_model
            ):
                logger.info("make auto actions for model")
                await self.mdata.make_default_action_model(
                    self.session, record.rec_name, record)

            await self.check_and_create_task_action(record)
        else:
            model_schema = await self.mdata.component_by_name(self.action.model)
            record = await self.save_copy(data=data, copy=True)
        if isinstance(record, dict):
            return record
        else:
            act_path = await self.compute_action_path(record)
            self.session.app['curr_data'] = record.get_dict()
            schema = {}
            if not isinstance(model_schema, dict):
                schema = model_schema.get_dict()
            return {
                "status": "ok",
                "link": f"{act_path}",
                "reload": True,
                "schema": schema,
                "data": record.get_dict()
            }

    async def delete_action(self, data={}):
        logger.info(
            f"delete_action -> model:{self.action.model} action_type:{self.action.type}, curr_ref:{self.curr_ref}")
        related_name = self.aval_related_name()
        self.data_model = await self.mdata.gen_model(self.action.model)
        record = await self.mdata.by_name(
            self.data_model, self.curr_ref)
        if self.action.model == "component":
            await self.mdata.clean_action_and_menu_group(record.rec_name)
        await self.mdata.set_to_delete_record(self.data_model, record)
        act_path = await self.compute_action_path(record)
        return {
            "status": "ok",
            "link": f"{act_path}",
            "reload": True
        }

    # TODO
    async def apiApp_action(self, data={}):
        logger.info(
            f"apiapp_action -> model:{self.action.model} action_type:{self.action.type}, curr_ref:{self.curr_ref}")
        model_schema = await self.mdata.component_by_name(self.action.model)
        data_model = await self.mdata.gen_model(self.action.model)
        record_data = data_model(**data)
        can_edit = await self.eval_editable(model_schema, record_data)
        if not can_edit:
            logger.error(f"Accesso Negato {record_data.rec_name}")
            return self.make_error_message(f"Accesso Negato {record_data.rec_name}")
        method_name = self.action.url

        if hasattr(self, method_name):
            data = await mtd(data)
        else:
            logger.error(f"No method name {method_name}")
        # save record
        record = await self.save_copy(data=data, eval_todo=False)
        # if is error record is dict
        if isinstance(record, dict):
            return record

        act_path = await self.compute_action_path(record)

        return {
            "status": "ok",
            "link": f"{act_path}",
            "reload": True,
            "schema": data_model.get_dict(),
            "data": record.get_dict()
        }

    async def system_action(self, data={}):
        pass
