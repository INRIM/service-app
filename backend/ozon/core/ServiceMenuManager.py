# Copyright INRIM (https://www.inrim.eu)
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
from .QueryEngine import QueryEngine
from .ModelData import ModelData
from .BaseClass import BaseClass, PluginBase
from pydantic import ValidationError
import logging
import pymongo
import requests
import httpx

logger = logging.getLogger(__name__)


class ServiceMenuManager(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class MenuManagerBase(ServiceMenuManager):
    btn_action_parser = {
        "save": "post",
        "copy": "post",
        "delete": "post",
        "window": False
    }

    @classmethod
    def create(cls, session: Session = None, pwd_context=None, app_code=""):
        self = MenuManagerBase()
        self.session = session
        self.app_code = app_code
        self.mdata = ModelData.new(session=session, pwd_context=pwd_context, app_code=self.app_code)
        self.acl = ServiceSecurity.new(session=session, pwd_context=pwd_context, app_code=app_code)
        self.qe = QueryEngine.new(session=session, app_code=app_code)
        self.contextual_buttons = []
        self.contextual_actions = []
        self.action = None
        self.action_model = None
        return self

    # async def make_settings(self):
    #     self.settings = await self.mdata.get_app_settings(app_code=self.app_code)

    async def get_menu(self):
        if self.session.app.get('nemu'):
            return self.session.app.get('nemu').copy()

    async def make_query_user(self, base_query=[]):
        user_query = await self.acl.make_user_action_query()
        pre_list = base_query
        if user_query:
            and_list = pre_list + user_query
        else:
            and_list = pre_list[:]
        return and_list

    async def get_basic_menu_list(self, admin=False):
        menu_group_model = await self.mdata.gen_model("menu_group")
        self.action_model = await self.mdata.gen_model("action")
        menu_grops_list = await self.mdata.get_list_base(
            menu_group_model, query=await self.qe.default_query(menu_group_model, {"admin": admin})
        )
        menu_groups = [i['rec_name'] for i in menu_grops_list]
        menu_list = []

        for rec_name in menu_groups:

            found_item = await self.mdata.get_list_base(
                self.action_model, query=await self.qe.default_query(self.action_model, {
                    "$and": await self.make_query_user([
                        {"action_type": "menu"},
                        {"menu_group": rec_name}
                        # {"menu_group": {"$in": menu_groups}}
                    ])
                })
            )
            if found_item:
                menu_list = menu_list + found_item[:]

        return menu_list[:]

    async def make_main_menu(self):
        logger.debug(f"make_main_menu only admin")
        if not self.session.is_admin:
            return [{}]

        self.contextual_actions = await self.get_basic_menu_list(admin=True)
        self.contextual_buttons = await self.make_buttons(self.contextual_actions, group_by_field="mode")
        logger.info(f"make_main_menu - > Done")
        return self.contextual_buttons[:]

    async def make_dashboard_menu(self):
        logger.info(f"make_dashboard_menu")
        menu_group_model = await self.mdata.gen_model("menu_group")
        menu_grops_list = await self.mdata.get_list_base(
            menu_group_model, query=await self.qe.default_query(menu_group_model, {"admin": False})
        )
        menu_g = {}
        for i in menu_grops_list:
            menu_g[i['rec_name']] = i['label']

        menu_list = await self.get_basic_menu_list()
        list_cards = []
        group = {}
        for rec in menu_list:
            card = BaseClass(**rec)
            # form = await self.mdata.component_by_name(card.model)
            c_model = await self.mdata.gen_model(card.model)
            if c_model:
                q_user = await self.make_query_user([
                    {"action_type": "window"},
                    {"component_type": "form"},
                    {"model": card.model}
                ])
                q = await self.qe.default_query(self.action_model, {"$and": q_user})
                act_list = await self.mdata.get_list_base(self.action_model, query=q)
                card_buttons = []
                if card.mode:
                    link = f"{card.action_root_path}/{card.rec_name}"
                else:
                    link = f"{card.action_root_path}"
                number = 0
                if card.mode == "list":
                    # list_query
                    list_query = {}
                    if card.list_query:
                        list_query = ujson.loads(card.list_query)
                    q = await self.qe.default_query(c_model, list_query)
                    number = await self.mdata.count_by_filter(c_model, q)
                    logger.info(number)
                card_buttons = [{
                    "model": card.model,
                    "icon": card.button_icon,
                    "action_type": card.action_type,
                    "content": link,
                    "mode": card.mode,
                    "label": card.title,
                    "number": number
                }]

                for rec_b in act_list:
                    card_btn = BaseClass(**rec_b)
                    writable = card_btn.write_access
                    has_model_access = card.model in self.session.app['model_write_access']
                    add = True
                    if writable and has_model_access:
                        add = self.session.app['model_write_access'].get(card.model)
                    cc_model = await self.mdata.gen_model(card_btn.model)
                    if add and cc_model:
                        if card_btn.mode:
                            link = f"{card_btn.action_root_path}/{card_btn.rec_name}"
                        else:
                            link = f"{card_btn.action_root_path}"
                        number = 0
                        if card_btn.mode == "list":
                            # list_query
                            list_query = {}
                            if cc_model:
                                if card_btn.list_query:
                                    list_query = ujson.loads(card_btn.list_query)
                                q = await self.qe.default_query(cc_model, list_query)
                                number = await self.mdata.count_by_filter(cc_model, q)
                        card_buttons.append({
                            "model": card_btn.model,
                            "icon": card_btn.button_icon,
                            "action_type": card_btn.action_type,
                            "content": link,
                            "label": card_btn.title,
                            "mode": card_btn.mode,
                            "number": number
                        })

                card = {
                    "model": card.model,
                    "group_id": card.menu_group,
                    "title": menu_g[card.menu_group],
                    "buttons": card_buttons
                }
                list_cards.append(card)

        logger.debug(f"make_dashboard_menu - > Done")
        return list_cards[:]

    async def make_action_buttons(self, list_actions, rec_name=""):
        logger.debug(f"make_action_buttons -> {len(list_actions)} items")
        list_buttons = []
        group = {}
        for rec in list_actions:
            if isinstance(rec, dict):
                item = BaseClass(**rec)
            else:
                item = rec
            rec_name_action = item.rec_name
            writable = item.write_access
            has_model_access = item.model in self.session.app['model_write_access']
            add = True
            if writable and has_model_access:
                add = self.session.app['model_write_access'].get(item.model)
            if add:
                if rec_name:
                    rec_name_action = rec_name
                btn_action_type = self.btn_action_parser.get(item.action_type)

                if item.action_type in self.btn_action_parser:
                    url_action = f"{item.action_root_path}/{item.rec_name}/{rec_name_action}"
                else:
                    url_action = f"{item.action_root_path}/{rec_name_action}/{item.rec_name}"

                if item.rec_name == rec_name_action or item.action_type not in self.btn_action_parser:
                    url_action = f"{item.action_root_path}/{rec_name_action}"
                    # TODO case item.rec_name == rec_name_action
                    # TODO is new element and need to be save before run other action type
                    # TODO exlude button type:  delete, copy, update, print, export, ecc...
                button = {
                    "model": item.model,
                    "key": item.rec_name,
                    "type": "button",
                    "label": item.title,
                    "leftIcon": item.button_icon,
                    "authtoken": self.session.token,
                    "req_id": self.session.req_id,
                    "btn_action_type": self.btn_action_parser.get(item.action_type),
                    "action_type": item.action_type,
                    "url_action": url_action,
                    "builder": item.builder_enabled
                }

                list_buttons.append(button)

        if not list_buttons:
            list_buttons.append(group)
        return list_buttons

    async def make_buttons(self, list_actions, group_by_field="", rec_name=""):
        logger.info(f"make_buttons list_actions -> {len(list_actions)} items")
        list_buttons = []
        group = {}
        for rec in list_actions:
            if isinstance(rec, dict):
                item = BaseClass(**rec)
            else:
                item = rec
            c_model = await self.mdata.gen_model(item.model)
            if c_model:
                rec_name_action = item.rec_name
                if rec_name:
                    rec_name_action = rec_name
                btn_action_type = self.btn_action_parser.get(item.action_type)

                if item.action_type in self.btn_action_parser:
                    url_action = f"{item.action_root_path}/{item.rec_name}/{rec_name_action}"
                else:
                    url_action = f"{item.action_root_path}/{rec_name_action}/{item.rec_name}"

                if item.rec_name == rec_name_action or item.action_type not in self.btn_action_parser:
                    url_action = f"{item.action_root_path}/{rec_name_action}"
                    # TODO case item.rec_name == rec_name_action
                    # TODO is new element and need to be save before run other action type
                    # TODO exlude button type:  delete, copy, update, print, export, ecc...
                button = {
                    "model": item.model,
                    "key": item.rec_name,
                    "type": "button",
                    "label": item.title,
                    "leftIcon": item.button_icon,
                    "authtoken": self.session.token,
                    "req_id": self.session.req_id,
                    "btn_action_type": self.btn_action_parser.get(item.action_type),
                    "url_action": url_action,
                    "builder": item.builder_enabled
                }

                if item.menu_group == "model":
                    val = item.model
                else:
                    val = item.data_value.menu_group
                    if not val:
                        val = "No Menu"
                if not group.get(val):
                    group[val] = []
                group[val].append(button)

        if not list_buttons:
            list_buttons.append(group)
        return list_buttons
