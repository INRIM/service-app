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

    async def get_basic_menu_list(self, admin=False, parent=""):
        menu_group_model = await self.mdata.gen_model("menu_group")
        self.action_model = await self.mdata.gen_model("action")

        menu_grops_list = await self.mdata.get_list_base(
            menu_group_model, query=await self.qe.default_query(
                menu_group_model,
                {"$and": [{"admin": admin}, {"parent": parent}]}
            )
        )
        menu_groups = []
        menu_list = []
        model_done = []
        logger.info(menu_list)
        menu_g = {}
        for i in menu_grops_list:
            found_item = await self.mdata.get_list_base(
                self.action_model, query=await self.qe.default_query(self.action_model, {
                    "$and": await self.make_query_user([
                        {"deleted": 0},
                        {"menu_group": i['rec_name']}
                    ])
                })
            )
            if found_item:
                if found_item[0]['model'] not in model_done:
                    model_done.append(found_item[0]['model'])
                    menu_list.append(
                        {
                            "model": found_item[0]['model'],
                            "menu_group": i['rec_name'],
                            "label": i['label']
                        }
                    )
            else:
                number = await self.mdata.count_by_filter(menu_group_model, {"parent": i['rec_name']})
                if number > 0:
                    menu_list.append(
                        {
                            "model": False,
                            "menu_group": i['rec_name'],
                            "label": i['label'],
                            "dashboard": True,
                            "content": f"/dashboard/{i['rec_name']}",
                            "mode": "list",
                            "action_type": "list",
                            "number": number,
                            "icon": "it-folder"
                        }

                    )

        return menu_list[:]

    async def make_main_menu(self) -> list:
        logger.debug(f"make_main_menu only admin")
        if not self.session.is_admin:
            return [{}]
        self.action_model = await self.mdata.gen_model("action")
        menu_group_model = await self.mdata.gen_model("menu_group")
        menu_grops_list = await self.mdata.get_list_base(
            menu_group_model, query=await self.qe.default_query(menu_group_model, {"admin": True})
        )
        self.contextual_buttons = await self.make_buttons(menu_grops_list, group_by_field="mode")
        logger.info(f"make_main_menu - > Done")
        return self.contextual_buttons[:]

    async def make_menu_item(self, card, rec_b):
        card_btn = BaseClass(**rec_b)
        has_model_access = card['model'] in self.session.app['model_write_access']
        writable = card_btn.write_access
        add = True
        if writable and has_model_access:
            add = self.session.app['model_write_access'].get(card['model'])
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
            return {
                "model": card_btn.model,
                "icon": card_btn.button_icon,
                "action_type": card_btn.action_type,
                "content": link,
                "label": card_btn.title,
                "mode": card_btn.mode,
                "number": number
            }.copy()
        return False

    async def make_dashboard_menu(self, parent=""):
        logger.info(f"make_dashboard_menu {parent}")
        menu_list = await self.get_basic_menu_list(parent=parent)
        logger.info(menu_list)
        list_cards = []
        group = {}
        for card in menu_list:
            if card['model']:
                c_model = await self.mdata.gen_model(card['model'])
                if c_model:
                    q_menu_user = await self.make_query_user([
                        {"action_type": "menu"},
                        {"component_type": {'$in': ["form", "resource", "layout"]}},
                        {"$or": [{"model": card['model']}, {"menu_group": card['menu_group']}]}
                    ])

                    q_user = await self.make_query_user([
                        {"action_type": "window"},
                        {"component_type": {'$in': ["form", "resource", "layout"]}},
                        {"$or": [{"model": card['model']}, {"menu_group": card['menu_group']}]}
                    ])
                    q_menu = await self.qe.default_query(self.action_model, {"$and": q_menu_user})
                    q = await self.qe.default_query(self.action_model, {"$and": q_user})

                    menu_list = await self.mdata.get_list_base(self.action_model, query=q_menu)
                    act_list = await self.mdata.get_list_base(self.action_model, query=q)

                    card_buttons = []

                    for rec_b in menu_list:
                        item = await self.make_menu_item(card, rec_b.copy())
                        if item:
                            card_buttons.append(item)

                    for rec_b in act_list:
                        item = await self.make_menu_item(card, rec_b.copy())
                        if item:
                            card_buttons.append(item)

                    card_m = {
                        "model": card['model'],
                        "group_id": card['menu_group'],
                        "title": card['label'],
                        "buttons": card_buttons
                    }
                    list_cards.append(card_m)
            else:
                card_m = {
                    "model": card['menu_group'],
                    "group_id": card['menu_group'],
                    "title": card['label'],
                    "buttons": [card.copy()]
                }
                list_cards.append(card_m)

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

    async def make_button_main_menu(self, rec):
        item = BaseClass(**rec)
        rec_name_action = item.rec_name
        # btn_action_type = self.btn_action_parser.get(item.action_type)

        if item.action_type in self.btn_action_parser:
            url_action = f"{item.action_root_path}/{item.rec_name}/{rec_name_action}"
        else:
            url_action = f"{item.action_root_path}/{rec_name_action}/{item.rec_name}"

        if item.rec_name == rec_name_action or item.action_type not in self.btn_action_parser:
            url_action = f"{item.action_root_path}/{rec_name_action}"

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
        return button

    async def make_buttons(self, list_actions, group_by_field="", rec_name=""):
        logger.info(f"make_buttons list_actions -> {len(list_actions)} items")
        list_buttons = []
        group = {}
        mg_done = []
        for mnu in list_actions:
            q_menu = await self.make_query_user([
                {"action_type": "menu"},
                {"menu_group": mnu['rec_name']}
            ])
            q_menud = await self.qe.default_query(self.action_model, {"$and": q_menu})
            menu_list = await self.mdata.get_list_base(self.action_model, query=q_menud)
            if menu_list:
                val = mnu['label']
                if not val:
                    val = "No Menu"
                if not group.get(val):
                    group[val] = []
                for rec_item in menu_list:
                    button = await self.make_button_main_menu(rec_item.copy())
                    group[val].append(button)

        if not list_buttons:
            list_buttons.append(group)
        return list_buttons
