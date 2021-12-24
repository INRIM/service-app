# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import os
import aiofiles
from os import listdir
from os.path import isfile, join
from pathlib import Path
import httpx
import logging
import ujson
from requests.utils import requote_uri
from .main.base.base_class import BaseClass, PluginBase
from .main.base.utils_for_service import requote_uri
import shutil
import yaml
from io import BytesIO
import aiofiles
from aiofiles.os import wrap
from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))

COMPOSE_CFG_TMP_FILE = "/app/ozon/base/docker_app_template/docker-compose.yml"
NGINX_CFG_TMP_FILE = "/app/ozon/base/docker_app_template/nginx.conf"
ENV_TMP_FILE = "/app/ozon/base/docker_app_template/env.tmp"


class SystemService(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class SystemServiceBase(SystemService):
    @classmethod
    def create(cls, settings, templates):
        self = SystemServiceBase()
        self.init(settings, templates)
        return self

    def init(self, settings, templates):
        self.settings = settings
        self.templates = templates
        self.theme = settings.theme
        self.stack = settings.stack
        self.movefile = wrap(shutil.move)
        self.copyfile = wrap(shutil.copyfile)

    async def check_and_init_service(self):
        logger.info("check_and_init_db")

    async def compute_check_and_init_service(self, path):
        logger.info(f"compute_check_and_init_db {path}")
        custom_builder_object_file = f"{path}/config.json"
        with open(custom_builder_object_file) as f:
            default_data = ujson.load(f)
        module_name = default_data.get("module_name", "")
        module_group = default_data.get("module_group", "")
        modeul_type = default_data.get("modeul_type", "")
        defaul_path = path
        default_data['defaul_path'] = defaul_path
        for node in default_data.get("templates"):
            nomefile = list(node.keys())[0]
            src = node[nomefile]
            pathfile = f"{defaul_path}/{namefile}"
            await self.import_template(pathfile, src)
        for node in default_data.get("static"):
            nomefile = list(node.keys())[0]
            src = node[nomefile]
            pathfile = f"{defaul_path}/{namefile}"
            await self.import_data(pathfile, src)

    async def import_template(self, namefile, src, force=False):
        logger.info(f"import_template components_file:{namefile}")
        dest = f"{self.settings.basedir}/core/themes/{self.theme}/templates/custom/{namefile}"
        if os.path.exists(src):
            if not os.path.exists(dest) or force:
                logger.info(f"copy {namefile}")
                await self.copyfile(src, dest)

    async def import_static(self, namefile, src, force=False):
        logger.info(f"import_static components_file:{namefile}")
        dest = f"{self.settings.basedir}/core/themes/{self.theme}/static/custom/{namefile}"
        if os.path.exists(src):
            if not os.path.exists(dest) or force:
                logger.info(f"copy {namefile}")
                await self.copyfile(src, dest)

    async def create_app_docker_compose(self, config):
        if not config['modeul_type'] == "app":
            return

        yml_tmp_dict = await self.read_yaml(COMPOSE_CFG_TMP_FILE)
        nginx_tmp_cfg = await self.read_text_file(NGINX_CFG_TMP_FILE)
        env_tmp_cfg = await self.read_text_file(ENV_TMP_FILE)

        service_cfg = yml_tmp_dict['tmp'].copy()
        nginx_cfg = yml_tmp_dict['nginx'].copy()

        new_compose_file = f"{default_data['defaul_path']}/docker/docker-compose.yml"
        new_nginx_file = f"{default_data['defaul_path']}/docker/nginx.conf"
        new_env_file = f"{default_data['defaul_path']}/docker/.env"

        app_name = config['module_name']
        app_group = default_data.get("module_group", "")
        port = config['port']

        yml_tmp_dict[app_name] = service_cfg
        yml_tmp_dict[app_name]['build']['args'] = [
            f"TZ={config['tz']}", f"APP_GROUP={app_group}", f"APP_NAME={app_name}"
        ]
        yml_tmp_dict['tmp'].pop()
        yml_tmp_dict[f"nginx-{app_name}"] = nginx_cfg
        yml_tmp_dict['nginx'].pop()
        yml_tmp_dict[f"nginx-{app_name}"]['depends_on'] = [app_name]
        yml_tmp_dict[f"nginx-{app_name}"]['ports'] = [f"{port}:{port}"]
        yml_tmp_dict[f"nginx-{app_name}"]['ports'] = [f"{port}:{port}"]
        await self.write_yaml(new_compose_file, yml_tmp_dict)
        new_cfg = nginx_tmp_cfg.format(**yml_tmp_dict)
        await self.write_text_file(new_nginx_file, new_cfg)
        env = f"""{env_tmp_cfg}
APP_NAME="{module_name}"
APP_DESC="{description}"
APP_VERSION="{app_version}"
TZ="{tz}"
WEB_CONCURRENCY={web_concurrency}
LOGO_IMG_URL="{logo_img_url}"
ADMINS={admins}
STACK={self.stack}
CLIENT_PORT={port}
        """.format(**config)
        await self.write_text_file(new_env_file, env)

    async def read_yaml(self, path):
        return await run_in_threadpool(lambda: self._read_yml_file(path))

    async def write_yaml(self, path: str, data: dict):
        return await run_in_threadpool(lambda: self._write_yml_file(path, data))

    async def read_text_file(self, path: str):
        async with aiofiles.open(path, mode='r', encoding='utf8') as infile:
            data = await infile.read()
        return data

    async def write_text_file(self, path: str, data: str, mode: str = "w"):
        async with aiofiles.open(path, mode=mode, encoding='utf8') as out_file:
            await out_file.write(data)
            await out_file.flush()

    @classmethod
    def _read_yml_file(cls, path):
        with aiofiles.open(path, mode='r', encoding='utf8') as infile:
            data = yaml.safe_load(infile)
        return data

    @classmethod
    def _write_yml_file(cls, path: str, data: dict):
        with aiofiles.open(path, mode='w', encoding='utf8') as out_file:
            yaml.dump(data, out_file, default_flow_style=False, allow_unicode=True)
