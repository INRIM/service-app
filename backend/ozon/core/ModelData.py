# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import sys
import os
import logging
import pymongo
import ujson
from .database.mongo_core import *
from .BaseClass import PluginBase
from fastapi.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ModelData(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class ModelDataBase(ModelData):

    @classmethod
    def create(cls):
        self = ModelDataBase()
        self.system_model = {
            "component": Component,
            "submission": Submission,
            "settingdata": settingData,
            "session": Session,
        }
        return self

    async def gen_model(self, model_name):
        model = False
        if model_name in self.system_model:
            model = self.system_model.get(model_name)
        else:
            component = await search_by_name(Component, model_name)
            if component:
                model = ModelMaker(
                    model_name, component.components).model
                await set_unique(model, 'rec_name')
        return model

    async def all(self, schema: Type[ModelType], sort=[], distinct=""):
        ASCENDING = 1
        """Ascending sort order."""
        DESCENDING = -1
        if not sort:
            #
            sort = [("list_order", ASCENDING), ("rec_name", DESCENDING)]
        return await search_all(schema, sort=sort)

    async def all_distinct(self, schema: Type[ModelType], distinct, query={}, additional_key=[]):
        list_data = await search_all_distinct(schema, distinct=distinct, query=query)
        return get_data_list(list_data, additional_key=additional_key)

    async def by_name(self, model, record_name):
        return await search_by_name(model, record_name)

    async def component_by_name(self, model_name):
        return await search_by_name(Component, model_name)

    async def component_by_type(self, model_type):
        return await search_by_type(Component, model_type=model_type)

    async def component_distinct_model(self):
        clausole = {"data_model": {"$eq": ""}}
        return await search_distinct(Component)

    async def get_list_base(
            self, data_model, fields=[], query={}, sort=[], limit=0, skip=0, model_type="",
            related_name="", merge_field="", row_action="", additional_key=[], with_count=False
    ):
        """
        additional_key handle formio id name (workaroud):
          - in form io id is defined ad '_id' but in standard mongodb id is defained 'id'
            passing replace ['rec_name', '_id'] if use formio builder to link resource in form.
            Before calling this method the params select sent from formio is '_id, title'
            in endpoint this field be going to replaced with 'rec_name', in get_data_list if
            replace is defined, adding record key '_id'  with value equal 'rec_name' to send
            a list data ecpected by fomiojs buider
        """
        logger.info(
            f"get_list_base -> data_model:{data_model}, fields: {fields}, query:{query}, sort:{sort},"
            f" model_type:{model_type}, related_name:{related_name}, merge_field: {merge_field}, row_action:{row_action}"
        )
        list_data = []
        if fields:
            fields = fields + default_list_metadata
        # TODO handle dynamic query
        if not query:
            if model_type:
                query = {"type": {"$eq": model_type}}

        return await self.search(
            data_model, fields=fields, query=query, sort=sort, limit=limit, skip=skip,
            merge_field=merge_field, row_action=row_action, parent=related_name, additional_key=additional_key)

    async def count_by_filter(self, data_model, query={}):
        return await count_by_filter(data_model, domain=query)

    def _check_update_date(self, obj_val):
        if not isinstance(obj_val, str):
            return obj_val
        if "isodate-" in obj_val:
            logger.info(f" render {obj_val}")
            x = obj_val.replace("isodate-", "")
            return datetime.strptime(x, '%Y-%m-%d %H:%M:%S')
        else:
            return obj_val

    def update(self, data):
        if isinstance(data, dict):
            for k, v in data.copy().items():
                if isinstance(v, dict):  # For DICT
                    data[k] = self.update(v)
                elif isinstance(v, list):  # For LIST
                    data[k] = [self.update(i) for i in v]
                else:  # Update Key-Value
                    data[k] = self._check_update_date(v)
        return data

    def scan_find_key(self, data, key):
        res = []
        if isinstance(data, dict):
            for k, v in data.items():
                res.append(k == key)
                if isinstance(v, dict):  # For DICT
                    res.append(self.scan_find_key(v, key))
                elif isinstance(v, list):  # For LIST
                    for i in v:
                        res.append(self.scan_find_key(i, key))
        return res[:]

    def flatten(self, l):
        for item in l:
            try:
                yield from self.flatten(item)
            except TypeError:
                yield item

    def check_key(self, data, key):
        logger.info("check key")
        res_l = self.scan_find_key(data, key)
        res_flat = list(self.flatten(res_l))
        try:
            i = res_flat.index(True)
            return True
        except ValueError:
            return False

    async def search_base(
            self, data_model: Type[ModelType], query={}, parent="", sort=[], limit=0, skip=0):

        ASCENDING = 1
        """Ascending sort order."""
        DESCENDING = -1
        """Descending sort order."""

        if not sort:
            #
            sort = [("list_order", ASCENDING), ("rec_name", DESCENDING)]

        if isinstance(query, dict) and not self.check_key(query, "deleted"):
            query.update({"deleted": {"$lte": 0}})

        if isinstance(query, dict) and not self.check_key(query, "parent") and parent:
            query.update({"parent": {"$eq": parent}})

        if isinstance(query, dict):
            q = self.update(query)
        else:
            q = query

        list_data = await search_by_filter(
            data_model, q, sort=sort, limit=limit, skip=skip
        )
        return list_data

    async def search(
            self, data_model: Type[ModelType], fields=[], query={}, sort=[], limit=0, skip=0,
            merge_field="", row_action="", parent="", additional_key=[], remove_keys=[]):

        if fields:
            fields = fields + default_list_metadata

        list_data = await self.search_base(
            data_model, query=query, parent=parent, sort=sort, limit=limit, skip=skip
        )
        return get_data_list(
            list_data, fields=fields, merge_field=merge_field, row_action=row_action, additional_key=additional_key)

    async def search_export(
            self, data_model: Type[ModelType], fields=[], query={}, sort=[], limit=0, skip=0,
            merge_field="", row_action="", parent="", additional_key=[], remove_keys=[]):

        if fields:
            fields = fields + default_list_metadata

        list_data = await self.search_base(
            data_model, query=query, parent=parent, sort=sort, limit=limit, skip=skip
        )

        return get_data_list(
            list_data, fields=fields, merge_field=merge_field,
            remove_keys=remove_keys, additional_key=additional_key)

    async def make_default_action_model(
            self, session, model_name, component_schema):
        logger.info(f" make_default_action_model {model_name}")
        ASCENDING = 1
        """Ascending sort order."""
        DESCENDING = -1
        """Descending sort order."""
        sort = [("list_order", ASCENDING), ("rec_name", DESCENDING)]
        q = {"$and": [{"model": "action"}, {"sys": True}, {"deleted": {"$lte": 0}}]}

        action_model = await self.mdata.gen_model("action")
        list_data = await search_by_filter(
            action_model, q, sort=sort, limit=0, skip=0
        )
        for action_tmp in list_data:
            data = action_tmp
            action = action_model(**data)
            action.model = model_name
            action.data_value['model'] = component_schema.title
            action.admin = component_schema.sys
            if action.action_type == "menu":
                action.title = f"Lista {component_schema.title}"
                action.data_value['title'] = f"Lista {component_schema.title}"
                action.menu_group = f"model"
                action.data_value['menu_group'] = "Model"

            action.rec_name = action.rec_name.replace("_action", f"_{model_name}")
            action.next_action_name = action.next_action_name.replace("_action", f"_{model_name}")
            await self.save_object(session, action)

    async def save_record(self, schema):
        await save_record(schema)

    async def save_all(self, schema):
        await save_all(schema)

    async def save_object(self, session, object_o, rec_name: str = "", model_name="", copy=False) -> Any:
        logger.info(f"save_object model:{model_name}, rec_name: {rec_name}, copy: {copy}")
        record_rec_name = object_o.rec_name
        if rec_name:
            source = await self.by_name(type(object_o), rec_name)
            if not copy:
                to_pop = default_fields[:]
                to_pop.append("rec_name")
                object_o = update_model(source, object_o, pop_form_newobject=to_pop)
            if session.user:
                object_o.update_uid = session.user.get('uid')

        object_o.update_datetime = datetime.now()

        if not rec_name or copy:
            object_o.create_datetime = datetime.now()
            object_o.owner_uid = session.user.get('uid')
            object_o.owner_name = session.user.get('full_name')
            object_o.owner_sector = session.user.get('divisione_uo', "")
            object_o.owner_function = session.user.get('user_function', "")

        if copy:
            if hasattr(object_o, "title"):
                object_o.title = f"{object_o.title} Copy()"
            if hasattr(object_o, "rec_name") and not object_o.rec_name == "":
                object_o.rec_name = f"{object_o.rec_name}_copy"
            else:
                object_o.rec_name = f"{model_name}.{object_o.id}"

        try:
            await save_record(object_o)

        except pymongo.errors.DuplicateKeyError as e:
            logger.error(f" Duplicte {e.details['errmsg']}")
            field = e.details['keyValue']
            key = list(field.keys())[0]
            val = field[key]
            return {
                "status": "error",
                "message": f"Errore Duplicato {key}: {val}",
                "model": model_name
            }
        return object_o

    async def set_to_delete_record(self, data_model: Type[ModelType], record):
        logger.info(f" set deleted model: {data_model}, record: {record}")
        return await set_to_delete_record(data_model, record)
