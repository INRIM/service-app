#!/usr/bin/env python
"""Add the demo test users (user/operator/manager) into their group_users
record for app_code=demo, plus the calendar-scheduler M2M service account
into the admin group (required by the ACL for its /client/run/* writes).
bootstrap.py only seeds 'admin' with the human admin uid; this covers the
rest. Run inside the app container:

    docker exec ozon-env-app uv run python seed_groups.py
"""
from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
log = logging.getLogger(__name__)

GROUP_MEMBERS = {
    "admin": ["service-account-calendar-scheduler"],
    "user": ["user"],
    "operator": ["operator"],
    "manager": ["manager"],
}


async def seed_group(cfg: dict, app_code: str, group: str, users: list[str]) -> None:
    from ozonenv.OzonEnv import OzonEnv

    rec_name = f"{group}-{app_code}"
    env = OzonEnv(cfg=cfg)
    await env.init_env()
    try:
        group_users_model = env.get("group_users")
        existing = await group_users_model.load({"rec_name": rec_name})
        if existing:
            current = list(getattr(existing, "users", []) or [])
            changed = False
            for u in users:
                if u not in current:
                    current.append(u)
                    changed = True
            if changed:
                setattr(existing, "users", current)
                await group_users_model.update(existing)
                log.info("group_users '%s' updated users=%s", rec_name, current)
            else:
                log.info("group_users '%s' already up-to-date users=%s", rec_name, current)
            return

        payload = {
            "rec_name": rec_name,
            "label": group.capitalize(),
            "app_code": app_code,
            "group": group,
            "users": users,
            "active": True,
            "deleted": 0,
            "default": False,
            "demo": False,
            "list_order": 1,
            "parent": "",
            "process_id": "",
            "process_task_id": "",
            "sys": False,
            "type": "form",
            "data_value": {
                "data_model": "group_users",
                "rec_name": rec_name,
                "label": group.capitalize(),
            },
        }
        new_rec = await group_users_model.new(data=payload)
        await group_users_model.insert(new_rec)
        log.info("group_users '%s' created users=%s", rec_name, users)
    finally:
        await env.close_env()


async def run() -> None:
    from app.app_settings import get_env_settings
    from app.deps.app_env import _build_ozon_cfg

    settings = get_env_settings()
    app_code = settings.app_code
    cfg = _build_ozon_cfg()

    for group, users in GROUP_MEMBERS.items():
        await seed_group(cfg, app_code, group, users)


if __name__ == "__main__":
    asyncio.run(run())
