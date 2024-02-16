# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import logging
import uuid
from .BaseClass import BaseClass, PluginBase
from .ModelData import ModelData
from .database.mongo_core import *

logger = logging.getLogger(__name__)


class ServiceSecurity(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class SecurityBase(ServiceSecurity):
    @classmethod
    def create(cls, session: Session = None, pwd_context=None, app_code=""):
        self = SecurityBase()
        self.init(session, pwd_context, app_code)
        return self

    def init(self, session, pwd_context, app_code=""):
        self.session = session
        self.app_code = app_code
        self.pwd_context = pwd_context
        self.mdata = ModelData.new(
            session=self.session,
            pwd_context=self.pwd_context,
            app_code=app_code,
        )

    # il modello ACL e' collogato al singolo componente
    # nel caso un model sia figlio di un altro model
    # le policy rules vengono copiate dal parent e poi possono essere modificate
    # si po' ad esempio dare un accesso ad un form di un progetto con restrizioni
    # ma lo si potra' raggiungere solo con un link diretto.

    async def check_action_app_code(self, action):
        # if is not admin app, check access action by app code
        if not self.app_code == "admin" and action.app_code != self.app_code:
            return False
        return True

    async def check_action_app_code(self, component):
        # if is not admin app, check access to component by app code
        if (
            not self.app_code == "admin"
            and self.app_code in component.app_code
        ):
            return False
        return True

    # TODO imp load schema and eval from rule model
    async def can_create(
        self, schema: BaseModel, data: BaseModel, action=None
    ):
        logger.debug(
            f"ACL can_create {self.session.user.get('uid')} -> {data.owner_uid} | user Admin {self.session.is_admin}"
        )
        create = False

        if (
            data.owner_uid == self.session.user.get("uid")
            or self.session.user_function == "resp"
        ):
            create = True

        if self.session.is_admin:
            return True

        logger.debug(
            f"ACL can_create {self.session.user.get('uid')} ->  {create}"
        )
        return create

    async def can_read(self, action=None):
        logger.info(
            f"ACL can_read {self.session.user.get('uid')}, "
            f"user Admin {self.session.is_admin}, action {action.rec_name}"
        )
        readable = True

        if action.no_public_user and self.session.is_public:
            readable = False

        if action.admin and not self.session.is_admin:
            readable = False

        # if is not admin app, check access action by app code
        if not await self.check_action_app_code(action):
            readable = False

        logger.debug(
            f"ACL can_read {self.session.user.get('uid')} ->  {readable}"
        )
        return readable

    async def can_update(
        self, schema: BaseModel, data: BaseModel, action=None
    ):

        logger.info(
            f"ACL can_update req user: {self.session.user.get('uid')} "
            f"-> data owner: {data.owner_uid},"
            f" req user Admin: {self.session.is_admin}"
        )

        editable = False

        if data.owner_uid == self.session.user.get("uid") or (
            self.session.function == "resp"
            and data.owner_sector_id == self.session.sector_id
        ):
            editable = True

        if not data.rec_name:
            editable = True

        if self.session.is_admin:
            editable = True

        logger.debug(
            f"ACL can_edit {self.session.user.get('uid')} ->  {editable}"
        )
        return editable

    async def can_update_fields(
        self, schema: BaseModel, data: BaseModel, action=None
    ):
        logger.debug(f"ACL Fields")
        fields = []
        logger.info(
            f"ACL editable_fields {self.session.user.get('uid')} ->  {fields}"
        )
        return fields

    async def can_delete(
        self, schema: BaseModel, data: BaseModel, action=None
    ):
        logger.debug(
            f"ACL can_delete {self.session.user.get('uid')} -> {data.owner_uid} | user Admin {self.session.is_admin}"
        )

        editable = False

        if (
            data.owner_uid == self.session.user.get("uid")
            or self.session.user_function == "resp"
        ):
            editable = True
        if self.session.is_admin:
            return True

        logger.debug(
            f"ACL can_edit {self.session.user.get('uid')} ->  {editable}"
        )
        return editable

    async def make_user_action_query(self):
        logger.debug(
            f"ACL user_action_query {self.session.user.get('uid')}  | user Admin {self.session.is_admin}"
        )
        query_list = []
        user = self.session.user
        if self.session.is_admin:
            return []

        function = user.get("user_function")
        query_list.append({"admin": False, "sys": False})
        if function == "resp":
            query_list.append(
                {"user_function": {"$elemMatch": {"$eq": ["user", "resp"]}}}
            )
        else:
            query_list.append({"user_function": "user"})
        if self.session.is_public:
            query_list.append({"no_public_user": False})

        return query_list
