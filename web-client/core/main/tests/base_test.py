# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
# from unittest import TestCase
import unittest
from .utils import readfile
from fastapi.templating import Jinja2Templates
from core.themes.ThemeConfig import ThemeConfig
from settings import *

default_fields = [
    "owner_uid",
    "owner_name",
    "owner_function",
    "owner_sector",
    "create_datetime",
    "update_uid",
    "update_datetime",
    "owner_personal_type",
    "owner_job_title",
    "owner_function_type",
    "owner_mail",
]


class CommonTestCase(unittest.TestCase):
    def setUp(self):
        super(CommonTestCase, self).setUp()
        self.forms_schema = readfile("/ozon/base/schema", "components.json")
        self.templates = Jinja2Templates(directory="core/themes")
        self.settings = get_settings()
        self.authtoken = "TEST"
        self.rec_name = ""
        self.model = ""
        self.theme_cfg = ThemeConfig.new(theme="italia")
        self.is_mobile = False
        self.editable_fields = []
        self.security_headers = {}
        self.builder = None

    def get_schema_name(self):
        for schema in self.forms_schema:
            if schema["rec_name"] == self.model:
                return schema.copy()

    def get_data(self, data_file_name, rec_name):
        datas = readfile("/ozon/base/data", f"{data_file_name}.json")
        for item in datas:
            if item["rec_name"] == rec_name:
                return item

    def get_context_app(self):
        return {
            "modes": ["standard"],
            "app_code": "test",
            "mode": "standard",
            "layout": "standard",
            "action_model": "action",
            "default_fields": default_fields[:],
            "model_write_access": {},
            "model_read_access": {},
            "model_write_access_fields": {},
            "fast_search": {},
            "queries": {},
            "settings": {},
            "action_name": "",
            "component_name": "",
            "submissison_name": "",
            "can_build": False,
            "builder": False,
            "save_session": False,
            "data": {},
            "breadcrumb": {},
        }

    def get_user_admin(self):
        return {
            "rec_name": "test-admin",
            "uid": "test.admin",
            "password": "test",
            "token": "TESTADMIN",
            "is_admin": True,
            "is_bot": True,
            "nome": "Admin Test",
            "mail": "admin@none.none",
            "cognome": "Admin",
            "full_name": "Admin Admin",
            "user_function": "user",
            "allowed_users": ["test.admin", "test.resp"],
        }

    def get_user_user(self):
        return {
            "rec_name": "test-admin",
            "uid": "test.user",
            "password": "user",
            "token": "TESTUSER",
            "is_admin": False,
            "is_bot": False,
            "nome": "User Test",
            "mail": "user@none.none",
            "cognome": "User",
            "full_name": "Test User",
            "user_function": "user",
            "allowed_users": [],
        }

    def get_user_resp(self):
        return {
            "rec_name": "test-admin",
            "uid": "test.resp",
            "password": "resp",
            "token": "TESTRESP",
            "is_admin": False,
            "is_bot": False,
            "nome": "Resp Test",
            "mail": "resp@none.none",
            "cognome": "Resp",
            "full_name": "Test Resp",
            "user_function": "resp",
            "allowed_users": ["test.admin", "test.resp"],
        }

    def get_context(self, form_data={}, user_type="admin"):
        """
        :param form_data:  dict with form data
        :param user_type:  can be "admin", "user", "resp"
        :return: dict context data
        """
        user = getattr(self, f"get_user_{user_type}")()
        app_ctx = self.get_context_app()
        return {"form": form_data.copy(), "user": user, "app": app_ctx}
