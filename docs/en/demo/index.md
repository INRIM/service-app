---
title: The executable demo
description: How inrim-forms-demo is built — plugin, Keycloak provisioning, orchestrator and secrets.
---

# The executable demo

[`inrim-forms-demo`](https://github.com/INRIM/inrim-forms-demo) is the
executable demo of service-app 3.0: the repo contains **only** the demo
(plugin, env, provisioning, orchestrator) — the backend and web-client
composes live in `service-app`, which `run_demo.sh` clones (gitignored) if
missing and fast-forward updates if present.

## How it is built

```
demo/
├── plugin/                   the "demo" plugin mounted at /plugins/demo
│   ├── config.json           manifest (module_name, schema, datas)
│   ├── schema/components.json  the "Modulo Dati Persona" form
│   └── data/
│       ├── menu_group.json   "Modulo Dati Persona" dashboard card
│       └── action.json       the form's 6 default actions
├── .env.demo                 backend env template (placeholders, no secrets)
├── .env.client-demo          web-client env template
├── docker-compose.demo.yml   override: adds Keycloak + mounts the plugin
├── provision_keycloak.sh     realm + web client + M2M client + users
├── seed_groups.py            group_users groups (user/operator/manager + M2M)
├── run_demo.sh               orchestrator: clone, env, up, provisioning, seed
├── clean_demo.sh             full cleanup
└── tests/                    provisioning script tests
service-app/                  service-app checkout (cloned here, gitignored)
gallery/                      screenshots used in the README
```

The demo form models are in `demo/models/*.py` — one Python model for each
system form (groups, group_users, action, menu_group, ext_service,
mail_template, calendar, camunda_process, field_acl_policy, ...): they are
the reference schemas for understanding what an Ozon component looks like.

## What `run_demo.sh up` does, in order

1. **prerequisites** — binaries, `docker compose` v2, Docker daemon;
2. **service-app checkout** — clone or fast-forward (best-effort, never
   clobbering local changes); overrides
   `SERVICE_APP_DIR`/`SERVICE_APP_REPO`/`SERVICE_APP_REF`;
3. **env** — generates the operational `.env` files from the templates,
   replacing placeholders with secrets;
4. **backend up** — `backend/docker-compose.yml` + `docker-compose.demo.yml`;
5. **wait for Keycloak**;
6. **Keycloak provisioning** — realm, web client, M2M client, users
   (idempotent); client secrets land in the generated `.env` and in
   `demo/.env.secrets`;
7. **recreate `app` + `calendar-scheduler`** with secrets, then
   `bootstrap.py` (plugin + admin) and `seed_groups.py` (groups);
8. **web-client up**.

## The compose override

`docker-compose.demo.yml` is the only override and does two things:

- **adds Keycloak** (the service-app compose declares the `keycloak_data`
  volume but not the service): `quay.io/keycloak/keycloak:26.0` in
  `start-dev`, embedded H2 — fine for the demo, not for production;
- **mounts the plugin** at `/plugins/demo` and the `models/` folder on the
  companion services.

## Container names

Since 3.0, `container_name`s are **mandatory** variables (`${...:?}`) read
from the `.env` files. The demo fills them with the historical names
(`ozon-env-app`, `ozon-env-app-db`, `ozon-env-mail-sender`,
`ozon-env-calendar-scheduler`, `ozon-env-identity-manager`,
`ozon-env-keycloak`, `demo-web`). Names are also **hostnames on the Docker
network**: if you change them, align `MONGO_URL`, `SCHEDULER_RUN_BASE_URL`
and `BACKEND_UPSTREAM`. The scripts contain no fixed names.

## Login: how everything connects

- The web-client sits on a single origin (`:4200`) and proxies `/api/*`,
  `/login`, `/logout`, `/auth/*` to the backend.
- The backend implements Keycloak login only (Authorization Code, BFF
  pattern): no local username/password login.
- `is_admin` and roles do not come from Keycloak: they come from
  `group_users`, keyed by `<group>-<app_code>`. `bootstrap.py` seeds only
  `admin`; `seed_groups.py` covers `user`/`operator`/`manager`.
- The `calendar-scheduler` is an M2M client (`client_credentials`): its
  service account must be in the `admin` group for `app_code=demo`
  (`seed_groups.py` adds it). Both clients carry a `demo` audience mapper:
  both tokens carry `demo` in the `aud` claim.

## Secrets

- `__GENERATE__` → `MONGO_PASS`, `SESSION_SECRET`, `KEYCLOAK_ADMIN_PASSWORD`:
  generated on first run, persisted to `demo/.env.secrets` (gitignored) and
  reused (the Mongo/Keycloak volumes are already initialized with those
  credentials);
- `__PROVISION__` → `KEYCLOAK_CLIENT_SECRET`,
  `SCHEDULER_OAUTH_CLIENT_SECRET`: produced by `provision_keycloak.sh` and
  written to the generated `.env`.

Operational `.env` files live in the local `service-app/` checkout
(gitignored) and are regenerated at every `run_demo.sh up`. To restart with
fresh secrets: `demo/clean_demo.sh`; to keep secrets:
`demo/clean_demo.sh --keep-secrets`.

## Known issues

- **`phoneNumber` not supported**: the `ModelMaker` has no `add_phoneNumber`;
  the field is logged as a caught startup error and ignored — the rest of the
  form works. An engine gap, not a porting mistake.
- **nginx and stale IPs**: `ozon-app-web` resolves the backend IP at startup —
  if you recreate the `app` container, recreate the web-client too
  (`run_demo.sh` always does).
- **Keycloak absent in service-app 3.0**: the override adds the IdP; if the
  upstream compose defines it again, the override's `keycloak:` block must be
  removed.

## Next

[Example modifications to try](examples.md): add a field, create a new
plugin, configure an ACL rule.