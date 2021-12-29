# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

import sys

sys.path.append("..")
import logging

from ozon.core.Ozon import OzonBase
from ozon.core.database.mongo_core import *

logger = logging.getLogger(__name__)

mod_config = {
    "module_name": "admin",
    "module_group": "inrim",
    "module_type": "module",
}


class OzonDatiRicerca(OzonBase):

    @classmethod
    def create(cls, pwd_context):
        self = OzonDatiRicerca()
        self.init(pwd_context)
        return self

    async def check_and_init_db(self):
        logger.info("check_db")
        await super().check_and_init_db()
        await self.compute_check_and_init_db(mod_config)
