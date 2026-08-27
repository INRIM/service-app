# service-app

Stack Docker per **ozon-env-app**: backend RAD multi-tenant (form Form.io,
CRUD generico su MongoDB, tema AGID/Bootstrap Italia) con autenticazione
Keycloak. Questo repo non contiene piu' il codice applicativo (backend e
frontend sono immagini Docker pubblicate) — contiene i **template
docker-compose** per far girare uno stack: backend condiviso + uno o piu'
frontend client.

## Struttura

```
backend/   backend condiviso: ozon-env-app + mongo + keycloak + companion
           service (mail-sender, calendar-scheduler, identity-manager)
app/       frontend per ogni singolo client (ozon-app-web: nginx + Angular);
           multi-tenant — un'istanza per client/app_code, stesso backend
```

## Concetti chiave

- **Multi-tenant per `APP_CODE`**: un solo backend serve piu' client. Ogni
  client (istanza di `app/`) porta il proprio `APP_CODE`; il backend lo
  seleziona per request (query param `?app_code=`, cookie, poi fallback su
  `APP_CODE`/`OZON_APP_CODE` d'ambiente).
- **Plugin su `/plugins/<app_code>/`**: le form/i modelli di un'app sono un
  "plugin" — una cartella con `config.json` (manifest: `module_name`,
  `schema`, `datas`, `depends`) + `schema/components.json` (le form, stesso
  formato Form.io della 2.x). Il plugin base (identita', gruppi, azioni) e'
  incluso nell'immagine; i plugin esterni si montano in `/plugins/<nome>`
  (bind mount o volume) e vengono scoperti e installati in Mongo all'avvio.
- **Auth solo Keycloak**: il backend implementa un login Authorization Code
  (pattern BFF) — `/login` reindirizza a Keycloak, `/auth/callback` scambia
  il code e apre una sessione propria (cookie). Non c'e' un login
  utente/password locale nel backend: serve un realm/client/utenti Keycloak
  veri (`AUTH_MODE=keycloak`). `is_admin` e i ruoli vengono dalla collection
  Mongo `group_users` (gruppi `admin`/`user`/`operator`/`manager`/...), non
  da ruoli Keycloak.
- **Frontend come reverse proxy single-origin**: `ozon-app-web` (nginx) sta
  su un'unica origin e proxya `/api/*`, `/login`, `/logout`, `/auth/*` verso
  il backend — niente CORS, cookie di sessione semplici.
- **Worker basati su `ozon-env`**: la libreria
  [`ozon-env`](https://github.com/INRIM/ozon-env) fornisce la base per creare
  i worker integrati nella piattaforma.

## Avviare un nuovo progetto

1. **Backend condiviso**: `cp backend/.env.example backend/.env`, valorizza
   almeno i nomi container univoci, `APP_CODE`, credenziali Mongo, `SESSION_SECRET`,
   `KEYCLOAK_ADMIN_PASSWORD`, `KEYCLOAK_CLIENT_SECRET` (quest'ultimo dopo
   aver creato il client su Keycloak). Poi:
   ```bash
   docker compose -f backend/docker-compose.yml up -d
   ```
2. **Provisioning Keycloak**: crea realm (`KEYCLOAK_REALM`, default
   `backend`), client confidenziale (`KEYCLOAK_CLIENT_ID`, default
   `backend-web`) con redirect URI = URL pubblico del frontend + `/auth/callback`,
   e gli utenti. Non c'e' (ancora) un tool generico di provisioning incluso.
3. **Frontend per ogni singolo client**: copia
   `app/docker-compose.client.example.yml` + `app/.env.example` in un
   `.env.client-<nome>` dedicato (porta, `APP_CODE` e
   `OZON_APP_WEB_CONTAINER_NAME` univoci e `BACKEND_UPSTREAM` coerente con
   `OZON_ENV_APP_CONTAINER_NAME` del backend),
   poi:
   ```bash
   docker compose -p ozon-client-<nome> -f docker-compose.client.example.yml \
     --env-file .env.client-<nome> up -d
   ```
4. **Plugin dell'app**: crea una cartella `config.json` + `schema/components.json`
   e montala in `/plugins/<app_code>` sul backend, poi lancia
   `bootstrap.py` dentro il container `app` per installarla in Mongo e
   seedare l'admin.

## Note

- Le immagini sono pubbliche e disponibili su GHCR
  ([`ghcr.io/inrim/ozon-env-app/*`](https://github.com/orgs/INRIM/packages?repo_name=ozon-env-app),
  `ghcr.io/inrim/ozon-formio`) e possono essere scaricate senza
  autenticazione. Se lavori con build locali, sovrascrivi le variabili
  `OZON_*_IMAGE` / `OZON_APP_WEB_IMAGE` nel tuo `.env`.
- I file `.env`/`.env.client-*` contengono segreti — non vanno committati.
- Tutti i `container_name` sono configurati nei rispettivi file `.env`: i
  valori devono essere univoci tra gli stack eseguiti sullo stesso host.

## Documentazione

La documentazione pubblica (italiano + inglese) vive in `docs/` e viene
pubblicata su GitHub Pages con MkDocs Material:

- Sito online: <https://inrim.github.io/service-app/>
- In locale: `pip install mkdocs-material mkdocs-static-i18n && mkdocs serve --dev-addr localhost:7800`
  → http://localhost:7800
  (fonte: `docs/*.it.md` + `docs/*.en.md`, nav in `mkdocs.yml`)
- Deploy: workflow `.github/workflows/docs.yml` (build strict + Pages)
- Container locale: `./run_docs.sh up` → http://localhost:7800
  (`down` per fermare, `build` per il sito statico in `site/`)
