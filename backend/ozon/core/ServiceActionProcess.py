# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

import logging

from .ServiceAction import ActionMain
# from ozon.settings import get_settings
from .database.mongo_core import *

logger = logging.getLogger(__name__)


class ActionProcessTask(ActionMain):
    @classmethod
    def create(
            cls,
            session: Session,
            service_main,
            action_name,
            rec_name,
            parent,
            process_id,
            iframe,
            execute,
            pwd_context,
            container_act="",
    ):
        self = ActionProcessTask()
        self.init(
            session,
            service_main,
            action_name,
            rec_name,
            parent,
            process_id,
            iframe,
            execute,
            pwd_context,
            container_act=container_act,
        )
        return self

    async def hendle_process_action(self, data={}):
        pass

    async def hendle_process_task_action(self, data={}):
        pass
