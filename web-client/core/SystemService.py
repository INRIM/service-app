# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import json
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
from aiofiles.os import wrap
import aiofiles
from fastapi.concurrency import run_in_threadpool
from jinja2 import Environment, FileSystemLoader, Template
from aiopath import AsyncPath

logger = logging.getLogger(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))

APP_TMP_PATH = "/app/ozon/base/docker_app_template"
COMPOSE_CFG_TMP_FILE = "docker-compose.yml"
NGINX_CFG_TMP_FILE = "nginx.conf"
ENV_TMP_FILE = "env.tmp"


class SystemService(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        if cls not in cls.plugins:
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
        self.super_admins = settings.admins
        self.movefile = wrap(shutil.move)
        self.copyfile = wrap(shutil.copyfile)

    async def check_and_init_service(self):
        logger.info("check_and_init_service")

    async def compute_check_and_init_service(self, path):
        logger.info(f"compute_init_service {path}")
        custom_builder_object_file = f"{path}/config.json"
        with open(custom_builder_object_file) as f:
            default_data = ujson.load(f)
        default_data['stack'] = self.stack
        module_name = default_data.get("module_name", "")
        module_group = default_data.get("module_group", "")
        module_type = default_data.get("module_type", "")
        module_label = default_data.get("modeul_label", "")
        no_update = default_data.get("no_update", True)
        defaul_path = path
        default_data['defaul_path'] = defaul_path
        for node in default_data.get("templates", []):
            namefile = list(node.keys())[0]
            src = f"{path}{node[namefile]}"
            await self.import_template(namefile, src, force=not no_update)
        for node in default_data.get("components", []):
            namefile = list(node.keys())[0]
            src = f"{path}{node[namefile]}"
            await self.import_components(namefile, src, force=not no_update)
        for node in default_data.get("static", []):
            namefile = list(node.keys())[0]
            src = node[namefile]
            pathfile = f"{defaul_path}/{namefile}"
            await self.import_data(pathfile, src)
        # chk_file = f"{default_data['defaul_path']}/docker/docker-compose.yml"
        # if module_type == "app" and not await run_in_threadpool(lambda: os.path.exists(chk_file)):
        #     await self.create_app_docker_compose(default_data)

    async def import_template(self, namefile, src, force=False):
        logger.info(f"import_template components_file:{src}")
        dest = f"{self.settings.basedir}/core/themes/{self.theme}/templates/custom/{namefile}"
        if os.path.exists(src):
            if not os.path.exists(dest) or force:
                logger.info(f"copy {namefile}")
                await self.copyfile(src, dest)

    async def import_components(self, namefile, src, force=False):
        logger.info(f"import_components components_file:{src}")
        dest = f"{self.settings.basedir}/core/themes/{self.theme}/templates/components/custom/{namefile}"
        if os.path.exists(src):
            if not os.path.exists(dest) or force:
                logger.info(f"copy to {dest}")
                await self.copyfile(src, dest)

    async def import_static(self, namefile, src, force=False):
        logger.info(f"import_static components_file:{namefile}")
        dest = f"{self.settings.basedir}/core/themes/{self.theme}/static/custom/{namefile}"
        if os.path.exists(src):
            if not await os.path.exists(dest) or force:
                logger.info(f"copy {namefile}")
                await self.copyfile(src, dest)

    async def create_app_docker_compose(self, config):
        if not config['module_type'] == "app":
            return
        file_loader = FileSystemLoader(APP_TMP_PATH)
        env = Environment(loader=file_loader)

        yml_tmp = await run_in_threadpool(lambda: env.get_template(COMPOSE_CFG_TMP_FILE))
        nginx_tmp = await run_in_threadpool(lambda: env.get_template(NGINX_CFG_TMP_FILE))
        # nginx_docker_cfg = await run_in_threadpool(lambda: env.get_template(NGINX_DOCKER_TMP_FILE))
        env_tmp_cfg = await run_in_threadpool(lambda: env.get_template(ENV_TMP_FILE))

        new_compose_file = f"{config['defaul_path']}/docker/docker-compose.yml"
        new_nginx_file = f"{config['defaul_path']}/docker/nginx.conf"
        # new_docker_file = f"{config['defaul_path']}/docker/Dockerfile-app"
        new_env_file = f"{config['defaul_path']}/docker/.env"

        await AsyncPath(f"{config['defaul_path']}/docker/").mkdir(parents=True, exist_ok=True)
        # merge super admins in admins app
        admins = config['admins']
        app_admins = self.super_admins + admins
        config['admins'] = json.dumps(app_admins)
        config['plugins'] = json.dumps(config['depends'])
        # create docker-compose
        yml_tmp_res = await run_in_threadpool(lambda: yml_tmp.render(config))
        await self.write_text_file(new_compose_file, yml_tmp_res)
        # create nginx.conf
        new_cfg = await run_in_threadpool(lambda: nginx_tmp.render(config))
        await self.write_text_file(new_nginx_file, new_cfg)

        new_env_cfg = await run_in_threadpool(lambda: env_tmp_cfg.render(config))
        await self.write_text_file(new_env_file, new_env_cfg)

    async def read_yaml(self, path):
        return await run_in_threadpool(lambda: self._read_yml_file(path))

    async def write_yaml(self, path: str, data: dict):
        return await run_in_threadpool(lambda: self._write_yml_file(path, data))

    async def read_text_file(self, path: str):
        logger.info(path)
        async with aiofiles.open(path, mode='r', encoding='utf8') as infile:
            data = await infile.read()
        return data

    async def write_text_file(self, path: str, data: str):
        logger.info(path)
        async with aiofiles.open(path, mode='w', encoding='utf8') as out_file:
            await out_file.write(data)
            await out_file.flush()

    @classmethod
    def _read_yml_file(cls, path):
        with open(path, mode='r', encoding='utf8') as infile:
            data = yaml.safe_load(infile)
        return data

    @classmethod
    def _write_yml_file(cls, path: str, data: dict):
        with open(path, mode='w', encoding='utf8') as out_file:
            yaml.dump(data, out_file, default_flow_style=False, allow_unicode=True)
