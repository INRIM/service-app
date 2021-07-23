# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from .mongodb.base_model import *
from .mongodb.mongo_base import *
from .mongodb.mongo_session import *
from .create_model import ModelMaker

# class JsonDatetime(datetime):
#     def __json__(self):
#         return '"isodate-%s"' % self.isoformat()
#
#
# datetime = JsonDatetime



