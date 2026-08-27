---
title: Step 5 — Workers and Camunda
description: How service-app integrates with Camunda 8 — application gateway, service tasks and ozon-env based workers.
---

# Workers and Camunda

<ol class="wizard-steps">
  <li class="wizard-done">Create a form</li>
  <li class="wizard-done">Components</li>
  <li class="wizard-done">Actions and groups</li>
  <li class="wizard-done">External services</li>
  <li class="wizard-current">Workers and Camunda</li>
</ol>

BPMN processes (Camunda 8) enter service-app from two sides:

1. **Application gateway** — the backend exposes `/gateway/camunda/...` to
   start processes and complete user tasks **inside the application ACL**:
   `start_camunda_gateway_process` requires `create` or `update` on the model
   configured on the process; `complete_many_camunda_gateway_tasks` gates
   `read` (model + record rule) before reading the record, whose content ends
   up in the process variables.
2. **Service task workers** — external processes that run Camunda jobs
   integrating the `ozon-env` application session.

## The `ozon_camunda_worker` package

In `workers/ozon_camunda_worker` sits the **common** package: a vertical
worker imports it, sets the `task_type` (job type), and specializes the
business logic in `session_app()`.

Components:

- `config.py` — `WorkerConfig.from_env` (Camunda REST v2 + oauth worker +
  ozon-env cfg);
- `camunda.py` — `CamundaJobClient` REST v2: `activate_jobs`, `complete_job`,
  `fail_job` (technical failure with remaining retries; at 0 → incident);
- `common.py` — `CommonWorker(OzonWorkerEnv)` + `serve()` (polling loop) +
  `process_job` (single job).

## Vertical worker template

```python
# workers/check_user/task.py
from ozonenv.core.BaseModels import BasicReturn
from ozon_camunda_worker import common

common.task_type = "ckeck_user"   # exact BPMN job type


class MyWorker(common.CommonWorker):
    async def session_app(self) -> BasicReturn:
        res = await super().session_app()
        if res.fail:
            return res
        # --- business logic with the ozon-env session ---
        uid = self.params.get("uid", "")
        user_model = self.get("user")
        user = await user_model.by_name(uid)
        responsible = getattr(user, "responsible_uid", "") if user else ""
        # business variables FLAT for the BPMN gateways
        return self.success_response(
            "ok",
            data={"variables": {"assignee": responsible, "is_resp": bool(responsible)}},
        )


async def run_camunda_task(variables: dict = None, job_type: str = "") -> BasicReturn:
    worker = MyWorker()
    ret = await worker.make_app_session(
        {**(variables or {}), "topic_name": common.task_type},
        cache_idx=common.task_type,
    )
    return ret


if __name__ == "__main__":
    import asyncio
    asyncio.run(common.serve(run_camunda_task))
```

Key rules:

- variables to send back to Camunda go **flat** in
  `data={"variables": {...}}` — BPMN gateways branch on those names
  (`is_resp`, `approved`, ...);
- `BasicReturn(fail=False)` → job completion with the produced variables;
  `BasicReturn(fail=True)` → **technical failure** (retries =
  `job.retries - 1`);
- `fail_job` is not a BPMN business error (that is `throw_job_error`,
  caught by an error boundary event): business decisions (approve/reject)
  stay **variables**, never fail;
- `make_app_session` already closes the env internally — no explicit
  `close_env()` needed.

## Worker auth

- **ozon-env session**: the worker works **directly on the DB** (Mongo via
  ozon-env), it does not call the app: no M2M token. `make_app_session`
  injects only a `job_token` (bot identity required by `init_auth`) and
  `session_is_api=True`. The involved user comes from the **Camunda
  variables** and is used in the business logic.
- **Camunda**: `CAMUNDA_OAUTH_*` (client_credentials) or no bearer if
  `CAMUNDA_AUTH_ENABLED=false`.

## Running and testing

```bash
# start/stop (interactive selection without arguments)
./start-workers.sh --all
./stop-workers.sh --all

# common package tests
PYTHONPATH=workers uv run python -m pytest workers/ozon_camunda_worker/tests/
```

The demo's `check_user` application uses the BPMN `attivita/test_request.bpmn`
with contractual job types (`ckeck_user`, `sed_message_approved`,
`sed_message_refused`) and pilots the flow through the app endpoints
`/gateway/camunda/...`. The real Camunda E2E test is opt-in:

```bash
APP_TOKEN=<app-session-token> ./run_camunda_integration_test.sh
```

## Path completed

You have seen the whole chain: forms → components → actions and groups →
external services → BPMN processes. To dig deeper:

- [ACL: model, record, field](../guides/acl.md)
- [Keycloak and session](../guides/keycloak-auth.md)
- [The demo and how to modify it](../demo/index.md)