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
from .default_data import default_data
import shutil
from aiofiles.os import wrap

logger = logging.getLogger(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))


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
        self.movefile = wrap(shutil.move)
        self.copyfile = wrap(shutil.copyfile)

    async def check_and_init_service(self):
        logger.info("check_and_init_service")
        for node in default_data.get("templates"):
            nomefile = list(node.keys())[0]
            src = node[nomefile]
            await self.import_template(nomefile, src)
        for node in default_data.get("static"):
            nomefile = list(node.keys())[0]
            src = node[nomefile]
            await self.import_data(nomefile, src)

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
