# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

import sys

sys.path.append("..")
import logging

from ozon.core.Ozon import OzonBase
from ozon.core.database.mongo_core import *

logger = logging.getLogger(__name__)

mod_config = {
    "module_name": "base",
    "module_group": "ozon",
    "modeul_type": "module",
}


class OzonOBase(OzonBase):

    @classmethod
    def create(cls, pwd_context):
        self = OzonOBase()
        self.init(pwd_context)
        return self

    async def check_and_init_db(self):
        logger.info("check_db")
        await self.compute_check_and_init_db(mod_config)
