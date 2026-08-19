# service-app

Stack Docker per **ozon-env-app**: backend RAD multi-tenant (form Form.io,
CRUD generico su MongoDB, tema AGID/Bootstrap Italia) con autenticazione
Keycloak. Questo repo non contiene piu' il codice applicativo (backend e
frontend sono immagini Docker pubblicate) — contiene i **template
docker-compose** per far girare uno stack: backend condiviso + uno o piu'
frontend client, piu' un plugin di esempio pronto all'uso.

## Struttura

```
backend/   backend condiviso: ozon-env-app + mongo + keycloak + companion
           service (mail-sender, calendar-scheduler, identity-manager)
app/       frontend per UN client (ozon-app-web: nginx + Angular);
           multi-tenant — un'istanza per client/app_code, stesso backend
demo/      esempio funzionante completo: plugin demo + provisioning
           Keycloak + script che avvia tutto in un colpo
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
  Vedi `demo/README.md` per un esempio completo commentato.
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

## Avviare un nuovo progetto

1. **Backend condiviso**: `cp backend/.env.example backend/.env`, valorizza
   almeno `APP_CODE`, credenziali Mongo, `SESSION_SECRET`,
   `KEYCLOAK_ADMIN_PASSWORD`, `KEYCLOAK_CLIENT_SECRET` (quest'ultimo dopo
   aver creato il client su Keycloak). Poi:
   ```bash
   docker compose -f backend/docker-compose.yml up -d
   ```
2. **Provisioning Keycloak**: crea realm (`KEYCLOAK_REALM`, default
   `backend`), client confidenziale (`KEYCLOAK_CLIENT_ID`, default
   `backend-web`) con redirect URI = URL pubblico del frontend + `/auth/callback`,
   e gli utenti. Non c'e' (ancora) un tool generico incluso qui — vedi
   `demo/provision_keycloak.sh` come riferimento/punto di partenza.
3. **Frontend per un client**: per ogni client, copia
   `app/docker-compose.client.example.yml` + `app/.env.example` in un
   `.env.client-<nome>` dedicato (porta, `APP_CODE`, `CLIENT_NAME` univoci),
   poi:
   ```bash
   docker compose -p ozon-client-<nome> -f docker-compose.client.example.yml \
     --env-file .env.client-<nome> up -d
   ```
4. **Plugin dell'app**: crea una cartella `config.json` + `schema/components.json`
   e montala in `/plugins/<app_code>` sul backend (vedi `demo/`), poi lancia
   `bootstrap.py` dentro il container `app` per installarla in Mongo e
   seedare l'admin.

## Provare subito: demo

Il modo piu' veloce per vedere lo stack funzionante — backend, Keycloak,
utenti di test, un plugin gia' pronto:

```bash
demo/run_demo.sh up
```

Dettagli, credenziali e architettura in [`demo/README.md`](demo/README.md).

## Note

- Le immagini sono pubblicate su GHCR
  ([`ghcr.io/inrim/ozon-env-app/*`](https://github.com/orgs/INRIM/packages?repo_name=ozon-env-app),
  `ghcr.io/inrim/ozon-formio`) — pacchetti **privati**: serve
  `docker login ghcr.io` con un PAT (scope `read:packages`) che abbia accesso
  all'org INRIM prima di `docker compose ... pull`/`up`. Se lavori con build
  locali, sovrascrivi le variabili `OZON_*_IMAGE` / `OZON_APP_WEB_IMAGE` nel
  tuo `.env` (vedi `demo/.env.demo` per un esempio).
- I file `.env`/`.env.client-*` contengono segreti — non vanno committati.
