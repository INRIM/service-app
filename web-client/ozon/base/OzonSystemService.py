# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import os
import sys

sys.path.append("..")

from core.SystemService import SystemServiceBase
import logging

logger = logging.getLogger(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))


class OzonSystemSrvice(SystemServiceBase):
    @classmethod
    def create(cls, settings, templates):
        self = OzonSystemSrvice()
        self.init(settings, templates)
        return self

    async def check_and_init_service(self):
        logger.info(f"check_and_init_service")
        await self.compute_check_and_init_service(basedir)
