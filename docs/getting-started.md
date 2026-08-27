---
title: Iniziare
description: Requisiti e avvio rapido dello stack service-app con la demo eseguibile.
---

# Iniziare

Il modo più rapido per vedere service-app funzionare è la demo eseguibile
[`inrim-forms-demo`](https://github.com/INRIM/inrim-forms-demo): un solo
comando tira su Keycloak, MongoDB, backend, companion service e web-client,
con un plugin di esempio già installato.

## Requisiti

- Docker Desktop attivo
- `git`, `curl`, `jq`, `openssl`

Le immagini arrivano da GHCR (`ghcr.io/inrim/ozon-env-app/*`,
`ghcr.io/inrim/ozon-formio`) e sono pubbliche: **nessun `docker login`**.

## Avvio

```bash
git clone https://github.com/INRIM/inrim-forms-demo.git
cd inrim-forms-demo
demo/run_demo.sh up
```

`run_demo.sh up` è idempotente e ri-eseguibile: clona (se manca) il checkout
di `service-app` nella root del repo, genera i `.env` coi segreti locali,
avvia lo stack, provisiona Keycloak (realm, client web, client M2M, utenti)
e seeda i gruppi.

Al termine:

| Cosa | URL | Credenziali |
|---|---|---|
| Web app | http://localhost:4200 | utenti demo, sotto |
| Backend API | http://localhost:7999 | — |
| Keycloak admin console | http://localhost:8082 | `admin` / password generata (salvata in `demo/.env.secrets`) |

Utenti demo (realm Keycloak `backend`), **username = password**: `admin`,
`user`, `operator`, `manager`. Sono mappati nei gruppi `admin`/`user`/
`operator`/`manager` della collection Mongo `group_users` per `app_code=demo`.

## Comandi

```bash
demo/run_demo.sh up       # installa (clone incluso) e avvia — idempotente
demo/run_demo.sh status   # stato dei container
demo/run_demo.sh down     # ferma i container (i dati restano nei volumi)
demo/run_demo.sh reset    # ferma e cancella anche i dati (mongo/keycloak)
demo/clean_demo.sh        # pulizia totale: container/volumi/immagini/orfani,
                          # .env generati e segreti locali
```

## Senza la demo: montare uno stack proprio

Il repo [`service-app`](https://github.com/INRIM/service-app) non contiene
codice applicativo: contiene i **template docker-compose** per far girare uno
stack con backend condiviso + uno o più frontend client.

1. **Backend condiviso** — `cp backend/.env.example backend/.env`, valorizza
   almeno i nomi container univoci, `APP_CODE`, credenziali Mongo,
   `SESSION_SECRET`, `KEYCLOAK_ADMIN_PASSWORD` e `KEYCLOAK_CLIENT_SECRET`
   (dopo aver creato il client su Keycloak), poi:

   ```bash
   docker compose -f backend/docker-compose.yml up -d
   ```

2. **Provisioning Keycloak** — crea il realm (`KEYCLOAK_REALM`, default
   `backend`), un client confidenziale (`KEYCLOAK_CLIENT_ID`, default
   `backend-web`) con redirect URI = URL pubblico del frontend +
   `/auth/callback`, e gli utenti.

3. **Frontend per ogni client** — copia
   `app/docker-compose.client.example.yml` + `app/.env.example` in un
   `.env.client-<nome>` dedicato (porta, `APP_CODE`), poi `up -d`.

I concetti chiave (multi-tenant per `APP_CODE`, plugin su `/plugins/`,
login BFF) sono descritti in [Architettura](architecture.md).