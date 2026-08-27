---
title: Getting started
description: Requirements and quick launch of the service-app stack with the executable demo.
---

# Getting started

The fastest way to see service-app running is the executable demo
[`inrim-forms-demo`](https://github.com/INRIM/inrim-forms-demo): a single
command brings up Keycloak, MongoDB, backend, companion service and
web-client, with a sample plugin already installed.

## Requirements

- Docker Desktop running
- `git`, `curl`, `jq`, `openssl`

Images come from GHCR (`ghcr.io/inrim/ozon-env-app/*`,
`ghcr.io/inrim/ozon-formio`) and are public: **no `docker login`**.

## Launch

```bash
git clone https://github.com/INRIM/inrim-forms-demo.git
cd inrim-forms-demo
demo/run_demo.sh up
```

`run_demo.sh up` is idempotent and re-runnable: it clones (if missing) the
`service-app` checkout into the repo root, generates the `.env` files with
local secrets, starts the stack, provisions Keycloak (realm, web client, M2M
client, users) and seeds the groups.

When done:

| What | URL | Credentials |
|---|---|---|
| Web app | http://localhost:4200 | demo users, below |
| Backend API | http://localhost:7999 | — |
| Keycloak admin console | http://localhost:8082 | `admin` / generated password (saved in `demo/.env.secrets`) |

Demo users (Keycloak realm `backend`), **username = password**: `admin`,
`user`, `operator`, `manager`. They are mapped to the `admin`/`user`/
`operator`/`manager` groups of the Mongo `group_users` collection for
`app_code=demo`.

## Commands

```bash
demo/run_demo.sh up       # install (clone included) and start — idempotent
demo/run_demo.sh status   # container status
demo/run_demo.sh down     # stop containers (data stays in volumes)
demo/run_demo.sh reset    # stop and delete data too (mongo/keycloak)
demo/clean_demo.sh        # full cleanup: containers/volumes/images/orphans,
                          # generated .env and local secrets
```

## Without the demo: running your own stack

The [`service-app`](https://github.com/INRIM/service-app) repo contains no
application code: it holds the **docker-compose templates** to run a stack
with a shared backend + one or more client frontends.

1. **Shared backend** — `cp backend/.env.example backend/.env`, fill in at
   least unique container names, `APP_CODE`, Mongo credentials,
   `SESSION_SECRET`, `KEYCLOAK_ADMIN_PASSWORD` and `KEYCLOAK_CLIENT_SECRET`
   (after creating the client on Keycloak), then:

   ```bash
   docker compose -f backend/docker-compose.yml up -d
   ```

2. **Keycloak provisioning** — create the realm (`KEYCLOAK_REALM`, default
   `backend`), a confidential client (`KEYCLOAK_CLIENT_ID`, default
   `backend-web`) with redirect URI = public frontend URL +
   `/auth/callback`, and the users.

3. **Frontend per client** — copy
   `app/docker-compose.client.example.yml` + `app/.env.example` into a
   dedicated `.env.client-<name>` (port, `APP_CODE`), then `up -d`.

The key concepts (multi-tenant by `APP_CODE`, plugins on `/plugins/`,
BFF login) are described in [Architecture](architecture.md).