---
title: Step 5 — I worker e Camunda
description: Come service-app si integra con Camunda 8 — gateway applicativo, service task e worker basati su ozon-env.
---

# I worker e Camunda

<ol class="wizard-steps">
  <li class="wizard-done">Creare un form</li>
  <li class="wizard-done">I componenti</li>
  <li class="wizard-done">Le action e i gruppi</li>
  <li class="wizard-done">Servizi esterni</li>
  <li class="wizard-current">Worker e Camunda</li>
</ol>

I processi BPMN (Camunda 8) entrano in service-app da due lati:

1. **Gateway applicativo** — il backend espone `/gateway/camunda/...` per
   avviare processi e completare task user **dentro l'ACL applicativa**:
   `start_camunda_gateway_process` richiede `create` o `update` sul model
   configurato sul processo; `complete_many_camunda_gateway_tasks` fa il gate
   `read` (model + record rule) prima di leggere il record, il cui contenuto
   finisce nelle variabili di processo.
2. **Worker service task** — processi esterni che eseguono i job di Camunda
   integrando la sessione applicativa `ozon-env`.

## Il package `ozon_camunda_worker`

In `workers/ozon_camunda_worker` c'è il package **common**: un worker
verticale lo importa, imposta il `task_type` (job type) e verticalizza la
business logic in `session_app()`.

Componenti:

- `config.py` — `WorkerConfig.from_env` (Camunda REST v2 + oauth worker +
  cfg ozon-env);
- `camunda.py` — `CamundaJobClient` REST v2: `activate_jobs`, `complete_job`,
  `fail_job` (fail tecnico con retries residui; a 0 → incident);
- `common.py` — `CommonWorker(OzonWorkerEnv)` + `serve()` (loop di polling) +
  `process_job` (singolo job).

## Template di worker verticale

```python
# workers/check_user/task.py
from ozonenv.core.BaseModels import BasicReturn
from ozon_camunda_worker import common

common.task_type = "ckeck_user"   # job type esatto del BPMN


class MyWorker(common.CommonWorker):
    async def session_app(self) -> BasicReturn:
        res = await super().session_app()
        if res.fail:
            return res
        # --- business logic con la sessione ozon-env ---
        uid = self.params.get("uid", "")
        user_model = self.get("user")
        user = await user_model.by_name(uid)
        responsible = getattr(user, "responsible_uid", "") if user else ""
        # variabili business FLAT per i gateway BPMN
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

Regole chiave:

- le variabili da rimandare a Camunda vanno **flat** in
  `data={"variables": {...}}` — i gateway BPMN ramificano su quei nomi
  (`is_resp`, `approved`, ...);
- `BasicReturn(fail=False)` → job completion con le variabili prodotte;
  `BasicReturn(fail=True)` → **fail tecnico** (retries = `job.retries - 1`);
- `fail_job` non è un business error BPMN (quello è `throw_job_error`,
  intercettato da un error boundary event): le decisioni di business
  (approva/rifiuta) restano **variabili**, non fail;
- `make_app_session` chiude già l'env internamente — niente `close_env()`
  esplicito.

## Auth dei worker

- **Sessione ozon-env**: il worker lavora **diretto sul DB** (Mongo via
  ozon-env), non chiama l'app: nessun token M2M. `make_app_session` inietta
  solo un `job_token` (identità bot richiesta da `init_auth`) e
  `session_is_api=True`. L'utente coinvolto arriva dalle **variabili
  Camunda** e viene usato nella business logic.
- **Camunda**: `CAMUNDA_OAUTH_*` (client_credentials) oppure nessun bearer se
  `CAMUNDA_AUTH_ENABLED=false`.

## Esecuzione e test

```bash
# avvio/arresto (selezione interattiva senza argomenti)
./start-workers.sh --all
./stop-workers.sh --all

# test del package common
PYTHONPATH=workers uv run python -m pytest workers/ozon_camunda_worker/tests/
```

L'applicazione `check_user` della demo usa il BPMN `attivita/test_request.bpmn`
con job type contrattuali (`ckeck_user`, `sed_message_approved`,
`sed_message_refused`) e pilota il flusso tramite gli endpoint app
`/gateway/camunda/...`. Il test E2E reale Camunda è opt-in:

```bash
APP_TOKEN=<token-sessione-app> ./run_camunda_integration_test.sh
```

## Percorso completato

Hai visto l'intera catena: form → componenti → action e gruppi → servizi
esterni → processi BPMN. Per approfondire:

- [ACL: model, record, field](../guides/acl.md)
- [Keycloak e sessione](../guides/keycloak-auth.md)
- [La demo e come modificarla](../demo/index.md)