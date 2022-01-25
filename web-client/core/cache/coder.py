import datetime
import json
import pickle  # nosec:B403
from decimal import Decimal
from typing import Any
from fastapi.encoders import jsonable_encoder


class Coder:
    @classmethod
    def encode(cls, value: Any):
        raise NotImplementedError

    @classmethod
    def decode(cls, value: Any):
        raise NotImplementedError


class PickleCoder(Coder):
    @classmethod
    def encode(cls, value: Any):
        return pickle.dumps(value)

    @classmethod
    def decode(cls, value: Any):
        return pickle.loads(value)  # nosec:B403
