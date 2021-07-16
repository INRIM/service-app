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
    def create(cls, session: Session = None):
        self = MenuManagerBase()
        self.session = session
        self.acl = ServiceSecurity.new(session=session)
        self.mdata = ModelData.new()
        self.contextual_buttons = []
        self.contextual_actions = []
        self.action = None
        self.action_model = None
        return self

    async def get_menu(self):
        if self.session.app.get('nemu'):
            return self.session.app.get('nemu').copy()

    async def get_basic_menu_list(self, admin=False):
        menu_group_model = await self.mdata.gen_model("menu_group")
        self.action_model = await self.mdata.gen_model("action")

        menu_grops_list = await self.mdata.get_list_base(
            menu_group_model, query={"admin": admin}
        )

        menu_groups = [i['rec_name'] for i in menu_grops_list]
        menu_list = await self.mdata.get_list_base(
            self.action_model, query={
                "$and": [
                    {"action_type": "menu"},
                    {"menu_group": {"$in": menu_groups}}
                ]
            }
        )
        return menu_list[:]

    async def make_main_menu(self):
        logger.info(f"make_main_menu only admin")
        if not self.session.is_admin:
            return [{}]

        self.contextual_actions = await self.get_basic_menu_list(admin=True)
        self.contextual_buttons = await self.make_buttons(self.contextual_actions, group_by_field="mode")
        logger.info(f"make_main_menu - > Done")
        return self.contextual_buttons[:]

    async def make_dashboard_menu(self):
        logger.info(f"make_dashboard_menu")
        menu_list = await self.get_basic_menu_list()
        list_cards = []
        group = {}
        for rec in menu_list:
            card = BaseClass(**rec)
            act_list = await self.mdata.get_list_base(
                self.action_model, query={
                    "$and": [
                        {"action_type": "window"},
                        {"component_type": "form"},
                        {"model": card.model}
                    ]
                }
            )
            card_buttons = []
            for rec_b in act_list:
                card_btn = BaseClass(**rec_b)
                if card_btn.mode:
                    link = f"{card_btn.action_root_path}/{card_btn.rec_name}"
                else:
                    link = f"{card_btn.action_root_path}"
                card_buttons.append({
                    "link": link,
                    "text": card_btn.title
                })

            card = {
                "title": card.title,
                "buttons": card_buttons
            }
            val = card.data_value.menu_group
            if not group.get(val):
                group[val] = []
            group[val].append(button)

        logger.info(f"make_dashboard_menu - > Done")
        return cards[:]

    async def make_action_buttons(self, list_actions, rec_name=""):
        logger.info(f"make_action_buttons -> {len(list_actions)} items")
        list_buttons = []
        group = {}
        for rec in list_actions:
            item = BaseClass(**rec)
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
            item = BaseClass(**rec)
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

    async def make_dashboard_cards(self, list_actions, group_by_field="", rec_name=""):
        logger.info(f"list_actions -> {len(list_actions)} items")
        list_buttons = []
        group = {}
        for rec in list_actions:
            item = BaseClass(**rec)
            if item.admin and not self.session.is_admin:
                pass
            else:
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
                if group_by_field:
                    if item.menu_group == "model":
                        val = item.model  # get(group_by_field, "NO VAL")
                    else:
                        val = item.data_value.menu_group
                        if not val:
                            val = "No Menu"
                    if not group.get(val):
                        group[val] = []
                    if item.admin and self.session.is_admin:
                        group[val].append(button)
                    else:
                        group[val].append(button)
                else:
                    if item.admin and self.session.is_admin:
                        list_buttons.append(button)
                    else:
                        list_buttons.append(button)

        if not list_buttons:
            list_buttons.append(group)
        return list_buttons
