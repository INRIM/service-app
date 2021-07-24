# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import logging
import uuid
from .BaseClass import BaseClass, PluginBase
from .database.mongo_core import *

logger = logging.getLogger(__name__)


class ServiceSecurity(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class SecurityBase(ServiceSecurity):

    @classmethod
    def create(cls, session: Session = None, pwd_context=None):
        self = SecurityBase()
        self.session = session
        self.pwd_context = pwd_context
        return self

    # il modello ACL e' collogato al singolo componente
    # nel caso un model sia figlio di un altro model
    # le policy rules vengono copiate dal parent e poi possono essere modificate
    # si po' ad esempio dare un accesso ad un form di un progetto con restrizioni
    # ma lo si potra' raggiungere solo con un link diretto.

    # TODO imp load schema and eval from rule model
    async def can_create(self, schema: Model, data: Model, action=None):
        logger.info(
            f"ACL can_create {self.session.user.get('uid')} -> {data.owner_uid} | user Admin {self.session.is_admin}")
        editable = False

        if data.owner_uid == self.session.user.get('uid') or self.session.user_function == "resp":
            editable = True

        if self.session.is_admin:
            return True

        logger.info(f"ACL can_edit {self.session.user.get('uid')} ->  {readable}")
        return editable

    async def can_read(self, schema: Model, data: List, action=None):
        logger.info(
            f"ACL can_read {self.session.user.get('uid')} -> {data.owner_uid} | user Admin {self.session.is_admin}")

        readable = True

        logger.info(f"ACL can_edit {self.session.user.get('uid')} ->  {readable}")
        return readable

    async def can_update(self, schema: Model, data: Model, action=None):
        logger.info(
            f"ACL can_update req user: {self.session.user.get('uid')} -> data owner: {data.owner_uid},"
            f" req user Admin: {self.session.is_admin}"
        )

        editable = False

        if data.owner_uid == self.session.user.get('uid') or self.session.user_function == "resp":
            editable = True

        if not data.rec_name:
            editable = True

        if self.session.is_admin:
            editable = True

        logger.info(f"ACL can_edit {self.session.user.get('uid')} ->  {editable}")
        return editable

    async def can_delete(self, schema: Model, data: Model, action=None):
        logger.info(
            f"ACL can_delete {self.session.user.get('uid')} -> {data.owner_uid} | user Admin {self.session.is_admin}")

        editable = False

        if data.owner_uid == self.session.user.get('uid') or self.session.user_function == "resp":
            editable = True
        if self.session.is_admin:
            return True

        logger.info(f"ACL can_edit {self.session.user.get('uid')} ->  {editable}")
        return editable

    async def make_user_action_query(self):
        logger.info(
            f"ACL user_action_query {self.session.user.get('uid')}  | user Admin {self.session.is_admin}")
        query_list = []
        user = self.session.user
        if self.session.is_admin:
            return []

        function = user.get('user_function')
        query_list.append({"admin": False, "sys": False})
        if function == "resp":
            query_list.append({
                "user_function": {"$elemMatch": {"$eq": ['user', 'resp']}}
            })
        else:
            query_list.append({"user_function": "user"})
        if self.session.is_public:
            query_list.append({"store_data": False})

        return query_list
