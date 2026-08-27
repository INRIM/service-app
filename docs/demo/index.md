---
title: La demo eseguibile
description: Com'è fatta inrim-forms-demo — plugin, provisioning Keycloak, orchestratore e segreti.
---

# La demo eseguibile

[`inrim-forms-demo`](https://github.com/INRIM/inrim-forms-demo) è la demo
eseguibile di service-app 3.0: il repo contiene **solo** la demo (plugin,
env, provisioning, orchestratore) — i compose di backend e web-client stanno
in `service-app`, che `run_demo.sh` clona (gitignorato) se manca e aggiorna
con fast-forward se c'è.

## Com'è fatta

```
demo/
├── plugin/                   il plugin "demo" montato in /plugins/demo
│   ├── config.json           manifest (module_name, schema, datas)
│   ├── schema/components.json  la form "Modulo Dati Persona"
│   └── data/
│       ├── menu_group.json   card dashboard "Modulo Dati Persona"
│       └── action.json       le 6 action di default della form
├── .env.demo                 template env del backend (segnaposto, no segreti)
├── .env.client-demo          template env del web-client
├── docker-compose.demo.yml   override: aggiunge Keycloak + monta il plugin
├── provision_keycloak.sh     realm + client web + client M2M + utenti
├── seed_groups.py            gruppi group_users (user/operator/manager + M2M)
├── run_demo.sh               orchestratore: clone, env, up, provisioning, seed
├── clean_demo.sh             pulizia totale
└── tests/                    test dello script di provisioning
service-app/                  checkout di service-app (clonato qui, gitignorato)
gallery/                      screenshot usati nel README
```

I modelli dei form della demo sono in `demo/models/*.py` — un model Python
per ognuna delle form di sistema (groups, group_users, action, menu_group,
ext_service, mail_template, calendar, camunda_process, field_acl_policy, ...):
sono gli schemi di riferimento per capire come è fatto un component Ozon.

## Cosa fa `run_demo.sh up`, in ordine

1. **prerequisiti** — binari, `docker compose` v2, demone Docker;
2. **checkout di service-app** — clone o fast-forward (best-effort, mai
   clobber di modifiche locali); override `SERVICE_APP_DIR`/`SERVICE_APP_REPO`/`SERVICE_APP_REF`;
3. **env** — genera i `.env` operativi dai template, sostituendo i segnaposto
   coi segreti;
4. **up del backend** — `backend/docker-compose.yml` + `docker-compose.demo.yml`;
5. **attesa Keycloak**;
6. **provisioning Keycloak** — realm, client web, client M2M, utenti
   (idempotente); i client secret finiscono nel `.env` generato e in
   `demo/.env.secrets`;
7. **ricreazione `app` + `calendar-scheduler`** coi secret, poi `bootstrap.py`
   (plugin + admin) e `seed_groups.py` (gruppi);
8. **up del web-client**.

## L'override compose

`docker-compose.demo.yml` è l'unico override e fa due cose:

- **aggiunge Keycloak** (il compose di service-app dichiara il volume
  `keycloak_data` ma non il servizio): `quay.io/keycloak/keycloak:26.0` in
  `start-dev`, H2 embedded — comodo per la demo, non per la produzione;
- **monta il plugin** in `/plugins/demo` e la cartella `models/` sui
  companion service.

## Nomi dei container

Dalla 3.0 i `container_name` sono variabili **obbligatorie** (`${...:?}`)
lette dai `.env`. La demo li valorizza coi nomi storici
(`ozon-env-app`, `ozon-env-app-db`, `ozon-env-mail-sender`,
`ozon-env-calendar-scheduler`, `ozon-env-identity-manager`,
`ozon-env-keycloak`, `demo-web`). I nomi sono anche **hostname sulla rete
Docker**: se li cambi vanno allineati `MONGO_URL`, `SCHEDULER_RUN_BASE_URL` e
`BACKEND_UPSTREAM`. Gli script non contengono nomi fissi.

## Login: come è collegato tutto

- Il web-client sta su una sola origin (`:4200`) e proxya `/api/*`, `/login`,
  `/logout`, `/auth/*` verso il backend.
- Il backend implementa solo login Keycloak (Authorization Code, pattern BFF):
  niente login utente/password locale.
- `is_admin` e i ruoli non vengono da Keycloak: vengono da `group_users`,
  keyed per `<group>-<app_code>`. `bootstrap.py` seeda solo `admin`;
  `seed_groups.py` copre `user`/`operator`/`manager`.
- Il `calendar-scheduler` è un client M2M (`client_credentials`): il suo
  service account deve stare nel gruppo `admin` per `app_code=demo`
  (`seed_groups.py` lo aggiunge). Entrambi i client hanno un audience mapper
  `demo`: entrambi i token portano `demo` nel claim `aud`.

## Segreti

- `__GENERATE__` → `MONGO_PASS`, `SESSION_SECRET`, `KEYCLOAK_ADMIN_PASSWORD`:
  generati al primo run, persistiti in `demo/.env.secrets` (gitignorato) e
  riusati (i volumi Mongo/Keycloak sono già inizializzati con quelle
  credenziali);
- `__PROVISION__` → `KEYCLOAK_CLIENT_SECRET`, `SCHEDULER_OAUTH_CLIENT_SECRET`:
  prodotti da `provision_keycloak.sh` e scritti nel `.env` generato.

Gli `.env` operativi stanno nel checkout locale di `service-app/`
(gitignorato) e sono rigenerati a ogni `run_demo.sh up`. Per ripartire con
segreti nuovi: `demo/clean_demo.sh`; per tenere i segreti:
`demo/clean_demo.sh --keep-secrets`.

## Problemi noti

- **`phoneNumber` non supportato**: il `ModelMaker` non ha `add_phoneNumber`;
  il campo viene loggato come errore catturato all'avvio e ignorato — il
  resto del form funziona. Lacuna del motore, non del porting.
- **nginx e IP stale**: `ozon-app-web` risolve l'IP del backend all'avvio —
  se ricrei il container `app`, ricrea anche il web-client (`run_demo.sh` lo
  fa sempre).
- **Keycloak assente in service-app 3.0**: l'IdP lo aggiunge l'override; se
  il compose upstream lo ridefinirà, il blocco `keycloak:` dell'override va
  rimosso.

## Prossimo

[Modifiche di esempio da provare](examples.md): aggiungere un campo,
creare un plugin nuovo, configurare una regola ACL.