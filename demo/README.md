# Demo stack

Porting della demo di [INRIM/service-app](https://github.com/INRIM/service-app)
(branch `2.4`, [`web-client/demo/demo`](https://github.com/INRIM/service-app/tree/2.4/web-client/demo/demo))
sul nuovo `ozon-env-app` (backend 3.0, multi-tenant, plugin su `/plugins/<app_code>`,
autenticazione Keycloak).

Avvia in un colpo solo: Keycloak + Mongo + `ozon-env-app` (con companion
service) + web-client, con il plugin `demo` caricato e 4 utenti di test
(`admin`, `user`, `operator`, `manager`).

## Quickstart

```bash
demo/run_demo.sh up      # avvia tutto (idempotente, ri-eseguibile)
demo/run_demo.sh down    # ferma i container (i dati restano nei volumi)
demo/run_demo.sh reset   # ferma e cancella anche i dati (mongo/keycloak)
demo/clean_demo.sh       # pulizia totale: container/volumi/orfani + .env
                         # generati + secret azzerati — riparti da un
                         # checkout pulito con demo/run_demo.sh up
```

Richiede Docker Desktop attivo, `curl` e `jq` sul sistema.

Al termine:

| Cosa | URL | Credenziali |
|---|---|---|
| Web app | http://localhost:4200 | vedi sotto |
| Backend API | http://localhost:7999 | — |
| Keycloak admin console | http://localhost:8081 | `admin` / vedi `demo/.env.demo` → `KEYCLOAK_ADMIN_PASSWORD` |

Utenti demo (realm Keycloak `backend`), **username = password**:
`admin`, `user`, `operator`, `manager`. Sono mappati nei rispettivi gruppi
(`admin-demo`, `user-demo`, `operator-demo`, `manager-demo`) nella collection
`group_users` per `app_code=demo`.

## Cosa contiene questa cartella

```
demo/
├── plugin/
│   ├── config.json           manifest del plugin (module_name, schema, datas)
│   ├── schema/components.json  la form "Modulo Dati Persona" portata dalla 2.4
│   └── data/
│       ├── menu_group.json   voce di menu "Demo"
│       └── action.json       list/form/save che agganciano la form al menu
├── .env.demo                 env del backend condiviso (copiato in backend/.env)
├── .env.client-demo          env del web-client (copiato in app/.env)
├── docker-compose.demo.yml   override: monta plugin/ in /plugins/demo su "app"
├── provision_keycloak.sh     realm + client web + client M2M calendar-scheduler
│                             + utenti Keycloak (idempotente)
├── seed_groups.py            aggiunge user/operator/manager ai gruppi group_users
│                             + il service account calendar-scheduler al gruppo admin
├── run_demo.sh               orchestratore: fa tutto quanto sopra in ordine
└── clean_demo.sh             pulizia totale (container/volumi/orfani + .env generati)
```

`docker-compose.demo.yml` e' l'unico override: monta il plugin nel backend
condiviso senza toccare `backend/docker-compose.yml`. Il resto (sorgente
immagini, rete, porte) usa direttamente `backend/docker-compose.yml` e
`app/docker-compose.client.example.yml`, coi default GHCR (nessun override
`OZON_*_IMAGE` in `.env.demo`/`.env.client-demo`).

## Come funziona il porting (per chi tocca il plugin)

Il nuovo `ozon-env-app` scopre i plugin guardando dentro `/plugins/<nome>/`:
se c'e' un `config.json` lo carica (vedi `app/plugins/__init__.py` +
`app/services/plugin_installer.py` nell'immagine `ozon-env-app`). Il manifest
minimo e':

```json
{
  "module_name": "demo",
  "schema": "/schema/components.json",
  "datas": [
    { "menu_group": "/data/menu_group.json" },
    { "action": "/data/action.json" }
  ],
  "depends": []
}
```

`schema` punta a un file di *component* (le form/i modelli, stesso formato
della 2.4) che viene upsertato nella collection `component` a ogni avvio
(salvo `no_update: true`). `datas` e' una lista di `{collection: path}` per
seed aggiuntivi, upsertati per `rec_name` allo stesso modo.

**Differenze rispetto al file 2.4 originale** (non e' un porting 1:1):
- `config.json` della 2.4 aveva un sacco di chiavi runtime
  (`internal_port`, `port`, `web_concurrency`, `theme`, `report_*`...) che
  appartenevano al vecchio modello "un deployment = un'app". Nel backend
  multi-tenant quelle chiavi non esistono piu': il manifest e' stato ridotto
  a quello che `plugin_installer.py` legge davvero.
- Il record component `modulo_dati_persona` aveva `"app_code": []` (lista
  vuota) invece di `""` (stringa) — tollerato dal vecchio modello, respinto
  dalla validazione Pydantic del nuovo. Va patchato a stringa vuota (fatto
  in `plugin/schema/components.json`).
- **La 2.4 aveva `"datas": []`** — nel vecchio monolite (un deployment =
  un'app) bastava il component per vedere la form. Nel nuovo backend
  multi-tenant, senza un `menu_group` + una tripletta di `action`
  (list → form → save, incatenate da `next_action_name`, stesso pattern del
  plugin `base`) la form esiste nel DB ma non compare da nessuna parte
  nell'interfaccia. `plugin/data/menu_group.json` + `plugin/data/action.json`
  coprono questo gap — non stavano nella 2.4 originale, sono stati aggiunti
  qui per rendere la form effettivamente raggiungibile dal menu.

## Login: come e' collegato tutto

Il web-client (`ozon-app-web`, nginx + Angular) sta su una sola origin
(`:4200`) e fa da reverse proxy verso il backend per `/api/*`, `/login`,
`/logout`, `/auth/*`: niente CORS, cookie di sessione single-origin.

Il backend implementa solo login **Keycloak** (Authorization Code, pattern
BFF): `/login` reindirizza a Keycloak, `/auth/callback` scambia il code,
crea la sessione e reimposta il cookie `ozon_session`. Non esiste un login
utente/password locale — per questo servono un realm, un client e utenti
Keycloak veri, provisionati da `provision_keycloak.sh`.

`is_admin` e i ruoli **non** vengono da Keycloak (nessun client role
richiesto): vengono da `group_users` in Mongo, keyed per `<group>-<app_code>`.
`bootstrap.py` (nell'immagine) seeda solo il gruppo `admin`; `seed_groups.py`
copre `user`/`operator`/`manager`.

### calendar-scheduler: anche lui via Keycloak (M2M)

`calendar-scheduler` non e' un utente umano: chiama l'endpoint
`/client/run/calendar_tasks/*` del backend come client `client_credentials`
(machine-to-machine). Serve quindi un secondo client Keycloak, service
account, separato dal client web (`provision_keycloak.sh` lo crea:
`calendar-scheduler`, `serviceAccountsEnabled: true`). Il suo utente
`service-account-calendar-scheduler` deve stare nel gruppo `admin` per
`app_code=demo` altrimenti l'ACL nega le scritture — `seed_groups.py` lo
aggiunge. L'override della demo imposta `OZON_TOKEN_AUDIENCE=demo` sul
backend e `SCHEDULER_OAUTH_AUDIENCE=demo` sullo scheduler. Il provisioning
Keycloak configura quindi, in modo idempotente, un audience mapper `demo`
sia sul client web sia sul client M2M: entrambi i token contengono
`demo` nel claim `aud`.

## Problemi noti

- **Campo "phoneNumber" non supportato**: `ModelMaker` del nuovo backend non
  ha un `add_phoneNumber`, quindi quel campo del form viene loggato come
  errore catturato all'avvio (`Error creation model object map: phoneNumber`)
  e ignorato — il resto del form funziona normalmente. E' una lacuna del
  motore, non uno sbaglio del porting.
- **Immagini da GHCR**: `backend/docker-compose.yml` e
  `app/docker-compose.client.example.yml` puntano di default a
  `ghcr.io/inrim/ozon-env-app/*` / `ghcr.io/inrim/ozon-formio`
  ([pacchetti INRIM](https://github.com/orgs/INRIM/packages?repo_name=ozon-env-app)),
  pubblici — nessun `docker login` richiesto. `demo/.env.demo` e
  `demo/.env.client-demo` non hanno override delle variabili `OZON_*_IMAGE`:
  se serve puntare a un'immagine locale o a un tag diverso, valorizzale li'.
- **nginx e IP stale**: `ozon-app-web` risolve l'IP del backend all'avvio e
  non lo aggiorna. Se ricrei il container `app` (es. dopo aver cambiato
  `KEYCLOAK_CLIENT_SECRET`) mentre il web-client e' gia' su, va ricreato
  anche lui — `run_demo.sh` lo fa gia' sempre all'ultimo step.

## Rigenerare i segreti

`demo/.env.demo` contiene segreti generati per questo ambiente locale
(`SESSION_SECRET`, `MONGO_PASS`, `KEYCLOAK_ADMIN_PASSWORD`). Non sono pensati
per essere committati/condivisi: `backend/.env` e `app/.env` sono copie
locali rigenerate a ogni `run_demo.sh up` e non vanno versionati.
