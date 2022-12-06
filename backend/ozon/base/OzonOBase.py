# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

import sys


import logging

from ozon.core.Ozon import OzonBase
from ozon.core.database.mongo_core import *

logger = logging.getLogger(__name__)

mod_config = {
    "module_name": "base",
    "module_group": "ozon"
}


class OzonOBase(OzonBase):

    @classmethod
    def create(cls, pwd_context, settings):
        self = OzonOBase()
        self.init(pwd_context, settings)
        return self

    async def check_and_init_db(self):
        logger.info("check_db")
        await self.compute_check_and_init_db(mod_config)
