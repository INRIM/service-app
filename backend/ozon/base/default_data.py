import os

basedir = os.path.abspath(os.path.dirname(__file__))

default_data = {
    "schema": f"{basedir}/schema/components.json",
    "datas": [
        {"menu_group": f"{basedir}/data/menu_group.json"},
        {"action_type": f"{basedir}/data/action_type.json"},
        {"user_type": f"{basedir}/data/user_type.json"},
        {"action": f"{basedir}/data/action.json"},
        {"user": f"{basedir}/data/user.json"}
    ]
}
