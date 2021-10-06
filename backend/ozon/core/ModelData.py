# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
import os
import logging
import pymongo
import ujson
from .database.mongo_core import *
from .BaseClass import PluginBase
from .QueryEngine import QueryEngine
from fastapi.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ModelData(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class ModelDataBase(ModelData):

    @classmethod
    def create(cls, session, pwd_context):
        self = ModelDataBase()
        self.init(session, pwd_context)
        return self

    def init(self, session, pwd_context):
        self.session = session
        self.pwd_context = pwd_context
        self.qe = QueryEngine.new(session=session)
        self.no_clone_field_keys = {}
        self.computed_fields = {}
        self.create_task_action = {}
        self.unique_fields = []
        self.asc = 1
        self.desc = -1
        self.system_model = {
            "component": Component,
            "session": Session,
            "attachment_trash": AttachmentTrash
        }

    async def gen_model(self, model_name):
        model = False
        if model_name in self.system_model:
            model = self.system_model.get(model_name)
        else:
            component = await search_by_name(Component, model_name)
            if component:
                mm = ModelMaker(
                    model_name, component.components)
                for field in mm.unique_fields:
                    await set_unique(mm.model, field)
                self.no_clone_field_keys = mm.no_clone_field_keys
                self.computed_fields = mm.computed_fields
                self.create_task_action = mm.create_task_action
                model = mm.model
        return model

    def clean_data_to_clone(self, data: dict):
        for k, v in self.no_clone_field_keys.items():
            if k in data and not k == "rec_name":
                data[k] = v
            if data.get("data_value") and data.get("data_value").get(k):
                data.get("data_value")[k] = v
        return data.copy()

    async def all(self, schema: Type[ModelType], sort=[], distinct=""):
        ASCENDING = 1
        """Ascending sort order."""
        DESCENDING = -1
        if not sort:
            #
            sort = [("list_order", ASCENDING), ("rec_name", DESCENDING)]
        return await search_all(schema, sort=sort)

    async def all_distinct(
            self, schema: Type[ModelType], distinct, query={}, additional_key=[], compute_label=""):

        ASCENDING = 1
        """Ascending sort order."""
        DESCENDING = -1

        # sort = [("title", DESCENDING)]
        querye = self.qe.default_query(schema, query)

        list_data = await search_all_distinct(schema, distinct=distinct, query=querye, compute_label=compute_label)
        return get_data_list(list_data, additional_key=additional_key)

    async def freq_for_all_by_field_value(
            self, schema: Type[ModelType], field, field_query, min_occurence=2, add_fields="", sort=-1,
            additional_key=[]
    ):

        list_data = await search_count_field_value_freq(
            schema, field=field, field_query=field_query, min_occurence=min_occurence, add_fields=add_fields, sort=sort)
        return get_data_list(list_data, additional_key=additional_key)

    async def by_name(self, model, record_name):
        return await search_by_name(model, record_name)

    async def user_by_token(self, token):
        return await search_user_by_token(User, token)

    async def by_uid(self, model, uid):
        return await search_by_uid(model, uid)

    async def component_by_name(self, model_name):
        return await search_by_name(Component, model_name)

    async def component_by_type(self, model_type):
        return await search_by_type(Component, model_type=model_type)

    async def component_distinct_model(self):
        clausole = {"data_model": {"$eq": ""}}
        return await search_distinct(Component)

    async def search_base(
            self, data_model: Type[ModelType], query={}, parent="", sort=[],
            limit=0, skip=0, use_aggregate=False):
        """
            
        """
        ASCENDING = 1
        """Ascending sort order."""
        DESCENDING = -1
        """Descending sort order."""

        if not sort:
            #
            sort = [("list_order", ASCENDING), ("rec_name", DESCENDING)]

        if use_aggregate:
            list_data = await aggregate(
                data_model, query, sort=sort, limit=limit, skip=skip
            )
        else:
            list_data = await search_by_filter(
                data_model, query, sort=sort, limit=limit, skip=skip
            )

        return list_data

    async def get_list_base(
            self, data_model, fields=[], query={}, sort=[], limit=0, skip=0, model_type="",
            parent="", merge_field="", row_action="", additional_key=[],
            use_aggregate=False
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
        logger.debug(
            f"get_list_base -> data_model:{data_model}, fields: {fields}, query:{query}, sort:{sort},"
            f" model_type:{model_type}, parent:{parent}, merge_field: {merge_field}, row_action:{row_action}"
        )
        list_data = []
        if fields:
            fields = fields + default_list_metadata

        return await self.search(
            data_model, fields=fields, query=query, sort=sort, limit=limit, skip=skip,
            merge_field=merge_field, row_action=row_action, parent=parent, additional_key=additional_key,
            use_aggregate=use_aggregate
        )

    async def count_by_filter(self, data_model, query={}) -> int:
        return await count_by_filter(data_model, domain=query)

    async def search(
            self, data_model: Type[ModelType], fields=[], query={}, sort=[], limit=0, skip=0,
            merge_field="", row_action="", parent="", additional_key=[], remove_keys=[], use_aggregate=False):

        if fields:
            fields = fields + default_list_metadata

        list_data = await self.search_base(
            data_model, query=query, parent=parent, sort=sort, limit=limit, skip=skip,
            use_aggregate=use_aggregate
        )
        return get_data_list(
            list_data, fields=fields, merge_field=merge_field,
            row_action=row_action, additional_key=additional_key, remove_keys=remove_keys)

    async def search_export(
            self, data_model: Type[ModelType], fields=[], query={}, sort=[], limit=0, skip=0,
            merge_field="", data_mode="raw", parent="", additional_key=[], remove_keys=[],
            use_aggregate=False):

        if fields:
            fields = fields + export_list_metadata

        list_data = await self.search_base(
            data_model, query=query, parent=parent, sort=sort, limit=limit, skip=skip,
            use_aggregate=use_aggregate
        )

        return get_data_list(
            list_data, fields=fields, merge_field=merge_field,
            remove_keys=remove_keys, additional_key=additional_key)

    async def make_action_task_for_model(
            self, session, model_name, component_schema, act_config={}):
        logger.info(f" make_default_action_model {model_name}")
        ASCENDING = 1
        """Ascending sort order."""
        DESCENDING = -1
        """Descending sort order."""
        sort = [("list_order", ASCENDING), ("rec_name", DESCENDING)]
        q = {"$and": [
            {"model": model_name},
            {"deleted": 0},
            {"action_type": "save"},
            {"list_query": "{}"}]}

        action_model = await self.gen_model("action")
        model = await self.gen_model(model_name)
        list_data = await search_by_filter(
            action_model, q, sort=sort, limit=0, skip=0
        )
        if list_data:
            src_action = list_data[0]
            action = action_model(**src_action)
            action.sys = component_schema.sys
            action.model = model_name
            action.list_order = await self.count_by_filter(model, query={"deleted": 0})
            action.data_value['model'] = component_schema.title
            action.admin = act_config.get("admin", False)
            if not action.admin:
                action.user_function = "user"
            if action.component_type:
                action.component_type = component_schema.type
            action.action_type = act_config.get("action_type", "task")
            action.data_value['action_type'] = act_config.get("action_type")
            action.type = act_config.get("type", "data")
            action.title = f"Task {component_schema.title}"
            action.data_value['title'] = f"Task {component_schema.title}"
            action.rec_name = f"{model_name}_{act_config.get('rec_name')}"
            action.data_value['rec_name'] = action.rec_name
            await self.save_object(session, action, model_name="action", model=action_model)

    async def make_default_action_model(
            self, session, model_name, component_schema):
        logger.info(f" make_default_action_model {model_name}")
        ASCENDING = 1
        """Ascending sort order."""
        DESCENDING = -1
        """Descending sort order."""
        sort = [("list_order", ASCENDING), ("rec_name", DESCENDING)]
        q = {"$and": [
            {"model": "action"},
            {"sys": True},
            {"deleted": 0},
            {"list_query": "{}"}]}

        action_model = await self.gen_model("action")
        menu_group_model = await self.gen_model("menu_group")
        model = await self.gen_model(model_name)
        list_data = await search_by_filter(
            action_model, q, sort=sort, limit=0, skip=0
        )
        group_created = False

        menu_groups = await self.count_by_filter(
            menu_group_model, query={"rec_name": model_name, "deleted": 0})
        if (
                menu_groups == 0 and
                (
                        component_schema.sys or not component_schema.type == 'resource'
                )
        ):
            menu = menu_group_model(
                **{
                    "rec_name": model_name,
                    "label": component_schema.title,
                    "admin": component_schema.sys
                })
            group_created = True
            await self.save_object(session, menu, model_name="menu_group", model=menu_group_model)

        for action_tmp in list_data:
            data = action_tmp
            action = action_model(**data)
            action.sys = component_schema.sys
            action.model = model_name
            action.list_order = await self.count_by_filter(model, query={"deleted": 0})
            action.data_value['model'] = component_schema.title
            action.admin = component_schema.sys
            if not action.admin:
                action.user_function = "user"
            if action.component_type:
                action.component_type = component_schema.type
            if action.action_type == "menu":
                action.title = f"Lista {component_schema.title}"
                action.data_value['title'] = f"Lista {component_schema.title}"
                if not group_created and component_schema.type == 'resource':
                    action.menu_group = 'risorse_app'
                    action.data_value['menu_group'] = "Risorse Apps"
                else:
                    action.menu_group = model_name
                    action.data_value['menu_group'] = component_schema.title

            action.rec_name = action.rec_name.replace("_action", f"_{model_name}")
            action.data_value['rec_name'] = action.rec_name
            action.next_action_name = action.next_action_name.replace("_action", f"_{model_name}")
            await self.save_object(session, action, model_name="action", model=action_model)

    async def save_record(self, schema):
        await save_record(schema)

    async def save_all(self, schema):
        await save_all(schema)

    async def set_user_data(self, record):
        record.owner_uid = self.session.user.get('uid')
        record.owner_name = self.session.user.get('full_name', "")
        record.owner_mail = self.session.user.get('mail', "")
        record.owner_sector = self.session.sector
        record.owner_sector_id = self.session.sector_id
        record.owner_personal_type = self.session.user.get("tipo_personale", "")
        record.owner_job_title = self.session.user.get("qualifica", "")
        record.owner_function = self.session.function
        return record

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    def diff(self, li1, li2):
        li_dif = [i for i in li1 + li2 if i not in li1 or i not in li2]
        return li_dif

    async def get_record_diff(self, session, object_o, rec_name: str = "", model_name="", copy=False):
        logger.info(f"model:{model_name}, rec_name: {rec_name}, copy: {copy}")
        # if not model:
        #     model = await self.gen_model(model_name)
        to_pop = default_list_metadata_fields[:]
        if rec_name:
            source = await self.by_name(type(object_o), rec_name)
            if not copy:
                if object_o.rec_name == rec_name:
                    to_pop.append("rec_name")
                object_o = update_model(source, object_o, pop_form_newobject=to_pop)
        new_dict = ujson.loads(object_o.json())
        [new_dict.pop(key) for key in to_pop]
        if rec_name and source:
            src_base = source.dict().copy()
            [src_base.pop(key) for key in to_pop]
            src_dict = src_base.copy()
            set_src_l = list(src_dict.items())
            set_new_l = list(new_dict.items())
            dict_diff = dict(self.diff(set_src_l, set_new_l))
        else:
            dict_diff = new_dict.copy()
        return dict_diff.copy()

    async def save_object(
            self, session, object_o, rec_name: str = "", model_name="", copy=False, model=False) -> Any:
        logger.info(f" model:{model_name}, rec_name: {rec_name}, copy: {copy}")
        if not model:
            model = await self.gen_model(model_name)
        source = await self.by_name(type(object_o), object_o.rec_name)
        if source:
            rec_name = object_o.rec_name
        if rec_name:
            if not source:
                source = await self.by_name(type(object_o), rec_name)
            if not copy:
                to_pop = default_fields[:]
                if object_o.rec_name == rec_name:
                    to_pop.append("rec_name")
                to_pop.append("list_order")
                object_o = update_model(source, object_o, pop_form_newobject=to_pop)
            if session.user:
                object_o.update_uid = session.user.get('uid')

        object_o.update_datetime = datetime.now()

        if not rec_name or copy:
            object_o.list_order = await self.count_by_filter(model, query={"deleted": 0})
            object_o.data_value['list_order'] = object_o.list_order
            object_o.create_datetime = datetime.now()
            object_o = await self.set_user_data(object_o)
            if model_name == "user":
                pw_hash = self.get_password_hash(object_o.password)
                object_o.password = pw_hash

        if copy:
            if hasattr(object_o, "title"):
                object_o.title = f"{object_o.title} Copy()"
            if (
                    hasattr(object_o, "rec_name") and
                    object_o.rec_name and model_name not in object_o.rec_name
            ):
                object_o.rec_name = f"{object_o.rec_name}_copy"
                if hasattr(object_o, "data_value"):
                    object_o.data_value['rec_name'] = object_o.rec_name
            else:
                object_o.rec_name = f"{model_name}.{object_o.id}"
        try:
            await save_record(object_o)

        except pymongo.errors.DuplicateKeyError as e:
            logger.error(f" Duplicate {e.details['errmsg']}")
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
        logger.info(f" data_model: {data_model}, record: {record}")
        return await set_to_delete_record(data_model, record)

    async def set_to_delete_records(self, data_model: Type[ModelType], query={}):
        logger.info(f" data_model: {data_model}, query: {query}")
        return await set_to_delete_records(data_model, query=query)

    async def delete_records(self, data_model: Type[ModelType], query={}):
        logger.info(f" delete_records data_model: {data_model}, query: {query}")
        return await delete_records(data_model, query=query)

    async def get_collections_names(self, query={}):
        collections_names = await get_collections_names(query=query)
        return collections_names

    async def clean_expired_to_delete_record(self):
        logger.info(f" clean expired to delete record ")
        c_names = await self.get_collections_names()
        for name in c_names:
            data_model = await self.gen_model(name)
            # if data_model.sys:
            #     logger.error("Try to delete a Sys model, consider to delete it via query")
            # else:
            logger.info(f" clean to delete {name} ")
            if not name == "session":
                await erese_all_to_delete_record(data_model)
        return {"status": "done"}

    def check_parse_json(self, str_test):
        try:
            str_test = ujson.loads(str_test)
        except ValueError as e:
            str_test = str_test.replace("'", "\"")
            try:
                str_test = ujson.loads(str_test)
            except ValueError as e:
                return False
        return str_test
