# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import sys
import os
from os import listdir
from os.path import isfile, join
import ujson
from ozon.settings import get_settings
from .database.mongo_core import *
from collections import OrderedDict
from pathlib import Path
from fastapi import Request
from .ServiceSecurity import ServiceSecurity
from .ServiceAction import ServiceAction
from .ServiceMenuManager import ServiceMenuManager
from .ModelData import ModelData
from .BaseClass import BaseClass, PluginBase
from pydantic import ValidationError
import logging
import pymongo
import requests
import httpx

logger = logging.getLogger(__name__)


# basedir = os.path.abspath(os.path.dirname(__file__))
# UPLOAD_FOLDER = f'/uploads'
# Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

class ServiceMain(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class ServiceBase(ServiceMain):

    @classmethod
    def create(
            cls, session: Session
    ):
        self = ServiceBase()
        self.session = session
        self.action_service = None
        self.mdata = ModelData.new()
        self.menu_manager = ServiceMenuManager.new(session=session)
        self.acl = ServiceSecurity.new(session=session)
        return self

    async def service_handle_action(
            self, action_name: str, data: dict = {}, rec_name: str = "",
            parent="", iframe="", execute=False, container_act=""):
        logger.info(f"service_handle_action -> name:{action_name}, rec_name:{rec_name}, "
                    f"execute:{execute}, data:{data}, container_act: {container_act}")
        if not data:
            data = {
                "limit": 0,
                "skip": 0,
                "sort": "",
                "query": {}
            }

        self.action_service = ServiceAction.new(
            session=self.session, action_name=action_name,
            rec_name=rec_name, parent=parent, iframe=iframe, execute=execute,
            container_act=container_act
        )

        return {
            "settings": {
                "app_name": get_settings().app_name,
                "app_version": get_settings().app_version,
                "logo_img_url": get_settings().logo_img_url
            },
            "menu": await self.menu_manager.make_main_menu(),
            "content": await self.action_service.compute_action(data=data)
        }

    async def service_get_layout(self, name):
        logger.info("service_get_default_layout")
        layout = await search_by_name(Component, rec_name=name)
        return {
            "settings": {
                "app_name": get_settings().app_name,
                "app_version": get_settings().app_version,
                "logo_img_url": get_settings().logo_img_url
            },
            "menu": await self.menu_manager.make_main_menu(),
            "schema": layout
        }

    async def service_get_schema(self, model_name):
        logger.info(f"service_get_schema by name {model_name}")
        # TODO add check rules for model
        schema = await self.mdata.component_by_name(model_name)
        return schema or {}

    async def service_reorder_record(self, data):
        logger.info(f"service_reorder_record by name {data}")
        # TODO add check rules for model
        model_data = await self.mdata.gen_model(data['model_name'])
        list_to_save = []
        for record_data in data['columns']:
            record = await self.mdata.by_name(model_data, record_data['key'])
            record.list_order = record_data['value']
            if not data['model_name'] == "component":
                record.data_value['list_order'] = record_data['value']
            list_to_save.append(record)
        await self.mdata.save_all(list_to_save)
        return {"status": "ok"}

    async def service_get_schemas_by_type(self, schema_type="form", query={}, fields=[], additional_key=[]):
        logger.info(
            f"service_get_schemas_by_type  schema_type:{schema_type}, query:{query}, "
            f"fields:{fields},additional_key:{additional_key}"
        )
        # TODO add check rules
        query = {
            "$and": [
                {"deleted": {"$eq": 0}},
                {"type": {"$eq": schema_type}}
            ]
        }
        data = await self.mdata.all_distinct(
            Component, "rec_name", query=query, additional_key=additional_key)
        return {
            "content": {
                "data": data or [],
            }
        }

    async def service_get_schemas_by_parent_and_type(
            self, parent_model, schema_type="form", fields=[], additional_key=[]):
        logger.info(f"service_get_schema by name {parent_model}")
        # TODO add check rules parent_model
        query = {
            "$and": [
                {"parent": {"$eq": parent_model}},
                {"deleted": {"$eq": 0}}
            ]
        }
        data = await self.mdata.get_list_base(
            Component, fields=fields, query=query, model_type=schema_type, additional_key=additional_key)
        return {
            "content": {
                "data": data or [],
            }
        }

    async def service_get_data_for_model(
            self, model_name, query={}, fields=[], additional_key=[]):
        logger.info(f"get_data_model {model_name}")
        # TODO add check read rules model_name
        data_model = await self.mdata.gen_model(model_name)
        data = await self.mdata.get_list_base(
            data_model, fields=fields, query=query)
        return {
            "content": {
                "data": data or []
            }
        }

    async def service_get_record(self, model_name, rec_name):
        logger.info(f"service_get_schema by name model_name:{model_name}, rec_name:{rec_name}")
        # TODO add check read rules for model
        schema = await self.mdata.component_by_name(model_name)
        data_model = await self.mdata.gen_model(model_name)
        data = await self.mdata.by_name(
            data_model, record_name=rec_name)
        if not data:
            data = {}
            can_edit = True
        else:
            can_edit = await self.acl.can_update(schema, data)
        return {
            "content": {
                "editable": can_edit,
                "model": model_name,
                "schema": schema or {},
                "data": data or {},
            }
        }

    async def service_component_distinct_model(self):
        logger.info(f"service_component_distinct_model")
        # TODO add check read rules for model
        query = {
            "$and": [
                # {"type": {"$eq": "form"}},
                {"deleted": {"$eq": 0}},
                {"data_model": {"$eq": ""}}
            ]
        }
        data = await self.mdata.all_distinct(
            Component, "rec_name", query=query)
        return {
            "content": {
                "data": data or [],
            }
        }

    async def get_remote_data_select(self, url, path_value, header_key, header_value_key):
        if path_value:
            url = f"{url}/{path_value}"
        header_value = get_settings().get_by_name(header_value_key)
        headers = {}
        remote_data = await self.get_remote_data(headers, header_key, header_value, url)
        return {
            "content": {
                "data": remote_data or [],
            }
        }

    async def get_remote_data(self, headers, header_key, header_value, url):
        logger.info(f"server get_remote_data --> {url}, header_key:{header_key}, header_value:{header_value} ")
        headers.update({
            "Content-Type": "application/json",
            header_key: header_value
        })
        async with httpx.AsyncClient() as client:
            res = await client.get(
                url=url, headers=headers
            )
        if res.status_code == 200:
            logger.info(f"server get_remote_data --> {url} SUCCESS ")
            return res.json()
        else:
            logger.info(f"server get_remote_data --> {url} Error {res.status_code} ")
            return {}

    async def export_data(self, model_name, query, parent_name=""):
        logger.info(f"export_data model:{model_name}, query:{query}, parent_name:{parent_name}")
        # if not isinstance(query, dict):
        #     query = {}
        schema = await self.mdata.component_by_name(model_name)
        data_model = await self.mdata.gen_model(model_name)
        data = await self.mdata.search_export(
            data_model, fields=[], query=query, parent=parent_name, remove_keys=["_id", "id"])
        return {
            "content": {
                "model": model_name,
                "schema": schema or {},
                "data": data or {},
            }
        }
