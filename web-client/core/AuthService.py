# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta
from .main.base.base_class import BaseClass, PluginBase
from .main.widgets_form import FormIoWidget
from .main.widgets_content import PageWidget
from .main.widgets_form_builder import FormIoBuilderWidget
from .main.widgets_layout import LayoutWidget
from .ContentService import ContentServiceBase
import logging

logger = logging.getLogger(__name__)


class AuthContentService(ContentServiceBase):

    @classmethod
    def create(cls, gateway, remote_data):
        self = AuthContentService()
        self.init(gateway, remote_data)
        return self

    async def get_login_page(self):
        logger.info("get_login_page")
        self.content = await self.gateway.get_remote_object(
            f"{self.local_settings.service_url}/login", params={}
        )
        form = await self.compute_form()
        self.layout = await self.get_layout()
        self.layout.rows.append(form)
        logger.info("Make Page Done")
        return self.layout.render_layout()