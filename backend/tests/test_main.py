# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from .conftest import test_app


def test_init(test_app):
    response = test_app.get("/action/list_form", headers={"referer": "localhost"})
    assert response.status_code == 200
    assert response.json() == {'action': 'redirect',
                               'url': 'https://test-auth.docker.ininrim.it/inrim-auth/login/forms?redirect=localhost',
                               'headers': {'referer': 'localhost'}}

# def test_status(test_app):
#     response = test_app.get("/status")
#     assert response.status_code == 200
#     assert response.json() == {"status": "live"}
#
