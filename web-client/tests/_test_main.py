from .main import app
from fastapi.testclient import TestClient
import pytest
from unittest import TestCase


class TestCommon(TestCase):
    def setup(self):
        self.user = "admin"
        self.password = "admin"
        client = TestClient(app)
