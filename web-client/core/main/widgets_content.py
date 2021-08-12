# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

import sys
from copy import deepcopy
import logging
import ujson

from .widgets_base import WidgetsBase, Request, BaseClass
import logging
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)


class PageWidget(WidgetsBase):

    @classmethod
    def create(
            cls, templates_engine: Jinja2Templates, session, request, settings, theme="italia", **kwargs):
        self = PageWidget()
        self.init(templates_engine, session, request, settings, theme=theme, **kwargs)
        return self

    def init(
            self, templates_engine: Jinja2Templates, session: dict, request, settings, disabled=False, theme="italia",
            **kwargs):
        super().init(templates_engine, session, request, theme=theme, **kwargs)
        self.disabled = disabled
        self.base_path = kwargs.get('base_path', "/")
        self.page_api_action = kwargs.get('page_api_action', "/")
        self.settings = settings
        self.authtoken = session.get('token')
        self.req_id = session.get('req_id')
        self.user = self.session.get("user")
        self.is_public_user = self.session.get("is_public")
        self.schema = {}
        self.ext_resource = False
        self.beforerows = []
        self.afterrrows = []
        self.menu_headers = []
        self.disabled = disabled
        self.user_token = {}

        self.user_name = ""
        self.user_avatr_url = ""
        self.uid = ""
        self.user_sector = ""
        self.email = ""
        self.user_function = "user"
        self.referee = ""
        self.context_data = {}
        self.resp_chain_list = []
        self.allowed_users = []
        self.create_datetime = None
        self.update_datetime = None
        self.components_change_ext_data_src = []
        self.list_metadata = [
            "id", "owner_uid", "owner_name", "owner_function", "owner_sector",
            "create_datetime", "update_uid", "update_datetime"]
        self.list_basic_metadata = [
            "owner_uid", "owner_name", "owner_function", "owner_sector",
            "create_datetime"]
        self.is_admin = False
        if self.authtoken:
            self.init_user()
        else:
            self.disabled = True
        logger.info("PageWidget init complete")

    def init_user(self):
        logger.info(f"init_user -> {self.user.get('uid')}")
        self.is_admin = self.session.get('is_admin')
        self.user = self.session.get("user")
        self.user_avatr_url = self.user.get('avatar')
        self.uid = self.user.get('uid')
        self.email = self.user.get("mail", "no_mail")
        self.user_name = self.user.get('full_name')
        if not self.user_name:
            self.user_name = f"{self.user.get('nome')} {self.user.get('cognome')}"
        self.user_sector = self.user.get("divisione_uo", "public")
        self.user_function = self.user.get('user_function')

    def update_users_data(self):
        if not self.owner_uid in self.allowed_users and not self.is_admin:
            self.disabled = True

    def _compute_form_data(self, node, form_data, parent_multi_row=False):
        data = node.compute_data(form_data)
        if node.component_items:
            for sub_node in node.component_items:
                data = self._compute_form_data(sub_node, data, parent_multi_row=node.multi_row)
        return data

    def _compute_form_data_table(self, node, form_data):
        # TODO dataGrid
        data = node.compute_data_table(form_data)

        if node.component_items:
            for sub_node in node.component_items:
                data = self._compute_form_data_table(sub_node, data)
        return data

    def _eval_logic(self, node, components_with_logic: list):
        if node.has_logic or node.has_conditions:
            if node.dataSrc and not node.table:
                self.components_change_ext_data_src.append(node)
            components_with_logic.append(node)
        if node.component_items:
            for sub_node in node.component_items:
                components_with_logic = self._eval_logic(sub_node, components_with_logic)
        return components_with_logic

    def get_login_act(self):
        return '/logout' if self.authtoken and not self.is_public_user else '/login/'

    def get_config(self, **context):
        today_date = self.dte.get_tooday_ui()
        base_prj_data = {
            "token": self.authtoken,
            "req_id": self.req_id,
            'app_name': self.settings.app_name,
            'version': self.settings.app_version,
            'env': "test",
            'login_act': self.get_login_act(),
            'login_user': self.user_name,
            'avatar': self.user_avatr_url,
            'today_date': today_date,
            "menu_headers": self.menu_headers,
            "beforerows": self.beforerows,
            "afterrrows": self.afterrrows,
            "backtop": self.backtop,
            "error": self.error,
            "export_button": self.export_btn,
            "rows": self.rows,
            "request": self.request,
            "base_path": self.base_path,
            "page_api_action": self.page_api_action,
            "logo_img_url": self.settings.logo_img_url
        }
        kwargs_def = {**context, **base_prj_data}
        return kwargs_def

    def render_page(self, template_name_or_list: str, **context):
        kwargs_def = self.get_config(**context)
        return self.response_template(template_name_or_list, kwargs_def)

    def response_custom(self, tmpname, cfg):
        return self.response_template(f"{tmpname}", cfg)

    def render_custom(self, tmpname, cfg):
        return self.render_template(f"{tmpname}", cfg)

    def deserialize_list_key_values(self, list_data):
        res = {item['name']: item['value'] for item in list_data}
        return res

    def check_default_metadata(self, form_data):
        for item in self.list_basic_metadata:
            if not form_data.get("item") or form_data.get("item") == "":
                form_data[item] = getattr(self, item)
        return form_data.copy()

    def deserialize_and_add_metadata(self, list_data):
        form_data = self.deserialize_list_key_values(list_data)
        form_data = self.check_default_metadata(form_data)
        form_data['create_datetime'] = datetime.now()
        return form_data

    def deserialize_and_update_metadata(self, form_data):
        form_data['update_datetime'] = datetime.now()
        return form_data

    def update_builder_data(self, record_id: str = "", datas={}, copy_data=False):
        # datas = self.request.json()

        if not record_id == "" and not copy_data:
            obj_data = self.deserialize_and_update_metadata(datas)
            obj_data['id'] = record_id
        else:
            obj_data = self.deserialize_and_add_metadata(datas)
        return obj_data

    def allowed_file(self, filename, allowed_extensions=['pdf']):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in allowed_extensions
