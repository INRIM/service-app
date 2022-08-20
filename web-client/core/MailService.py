# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import httpx
import logging

import ujson
import json
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from datetime import datetime, timedelta
from .main.base.base_class import BaseClass, PluginBase
from .AttachmentService import AttachmentService
import shutil
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from .main.widgets_content import PageWidget
from jinja2 import Template
from fastapi.concurrency import run_in_threadpool

import logging

logger = logging.getLogger(__name__)


class MailService(AttachmentService):

    @classmethod
    def create(cls, gateway, remote_data):
        self = MailService()
        self.init(gateway, remote_data)
        return self

    async def render_and_send(
            self, server_cfg, template_data, context_data):
        logger.info("start")
        context_data['app']['base_url'] = str(self.request.base_url)[:-1]

        data = context_data.get('form', {}).copy()
        datau = context_data.get('user', {}).copy()
        data_app = context_data.get('app', {}).copy()

        # logger.info(f"start {data}")

        if data:
            if not template_data.__dict__:
                logger.error(f"No template data is defined for {data}")
                return {}
            form_data = BaseClass(**data)
            user_data = BaseClass(**datau)
            app_data = BaseClass(**data_app)

            conf = ConnectionConfig(
                MAIL_USERNAME=server_cfg.mailServerUser,
                MAIL_PASSWORD=server_cfg.MAIL_PASSWORD,
                MAIL_FROM=server_cfg.MAIL_FROM,
                MAIL_PORT=int(server_cfg.port),
                MAIL_SERVER=server_cfg.MAIL_SERVER,
                MAIL_TLS=server_cfg.MAIL_TLS,
                MAIL_SSL=server_cfg.MAIL_SSL,
                MAIL_DEBUG=1,
                USE_CREDENTIALS=server_cfg.USE_CREDENTIALS,
                VALIDATE_CERTS=server_cfg.VALIDATE_CERTS
            )

            page = PageWidget.create(
                templates_engine=self.templates, session=self.session,
                request=self.request,
                settings=self.session.get('app', {}).get("settings",
                                                         self.local_settings.dict()).copy()
            )

            subject = page.render_str_template(
                template_data.subject,
                {"form": form_data, "user": user_data, "app": app_data})

            recipient = page.render_str_template(
                template_data.recipient,
                {"form": form_data, "user": user_data, "app": app_data})

            html_base_msg = page.render_str_template(
                template_data.corpoDellaMail,
                {"form": form_data, "user": user_data, "app": app_data}
            )

            template_mail_base = page.theme_cfg.get_template("mail",
                                                             "mail_doc")

            values = {
                "html": html_base_msg
            }

            messagec = page.render_template(
                template_mail_base, values
            )

            message = MessageSchema(
                subject=subject,
                recipients=recipient.split(","),
                # List of recipients, as many as you can pass
                html=messagec
            )
            # logger.info(conf)
            # logger.info(message)
            fm = FastMail(conf)

            try:
                await fm.send_message(message)
                return {"status": "ok"}
            except Exception as e:
                logger.error(str(e), exc_info=True)
                return {"status": "error", "msg": str(e)}
            # logger.info(res) res is always None
        return {"status": "error", "msg": 'no data'}

    async def send_email(self, form_data, tmp_name=""):
        logger.info("start")
        context_data = self.session.copy()
        context_data['form'] = form_data.copy()
        model_name = self.content.get('model')

        template_url = f"/mail_template/{model_name}"
        if tmp_name:
            template_url = f"{template_url}/{tmp_name}"

        template_content = await self.gateway.get_remote_object(template_url,
                                                                params={})

        template_data = BaseClass(
            **template_content.get("content").get("data", {}).copy())

        if template_data.__dict__:
            server_name_url = f"/mail_server/{template_data.server}"
            server_content = await self.gateway.get_remote_object(
                server_name_url, params={})

            server_cfg = BaseClass(
                **server_content.get("content").get("data", {}).copy())

            return await self.render_and_send(server_cfg, template_data,
                                              context_data)
        else:
            logger.error(
                f"Server not found, No template data is defined for {form_data}")
            return {"status": "error",
                    "msg": f'Server not found, No template data is defined for {form_data}'}

    async def after_form_post_handler(self, remote_response,
                                      submitted_data) -> dict:
        logger.info(f"check and send mail is new? --> {self.is_create}")
        response = await super().after_form_post_handler(remote_response,
                                                         submitted_data)
        content = response.get("content").copy()
        if "error" in content.get('status', "") or not content.get('schema'):
            return response.copy()
        schema = self.content.get('schema')
        send_mail_create = int(
            schema.get("properties", {}).get("send_mail_create", "0"))
        send_mail_update = int(
            schema.get("properties", {}).get("send_mail_update", "0"))
        remote_data = content.get("data", {}).copy()
        res_mail = {}
        if send_mail_create == 1 and self.is_create:
            res_mail = await self.send_email(remote_data)
        if send_mail_update == 1 and not self.is_create:
            res_mail = await self.send_email(remote_data)
        if res_mail.get("status", "") == "error":
            logger.error(res_mail)
            return res_mail

        return remote_response.copy()
