---
title: Keycloak e sessione
description: Come funziona l'autenticazione in service-app — Keycloak OIDC, pattern BFF, cookie di sessione, separazione autenticazione/autorizzazione.
---

# Keycloak e sessione applicativa

## Separazione delle responsabilità

- **Keycloak** gestisce autenticazione e SSO (OIDC).
- **Il backend** (`ozon-env-app`) genera e possiede la sessione applicativa.
- **Il frontend** non costruisce né falsifica identità: non contiene segreti
  e non gestisce token.

Il model di sessione resta quello canonico di `ozon-env`
(`ozonenv.core.BaseModels.Session`); il backend non definisce un model
sessione alternativo.

## Il flusso (pattern BFF)

1. `/login` reindirizza il browser a Keycloak (Authorization Code).
2. `/auth/callback` scambia il code, crea la sessione applicativa e
   reimposta il cookie `ozon_session` (httponly) + `ozon_csrf`.
3. Il web-client (nginx) fa da reverse proxy single-origin per
   `/api/*`, `/login`, `/logout`, `/auth/*` — niente CORS, cookie semplici.
4. Le richieste autenticate viaggiano col cookie; le chiamate mutanti
   aggiungono l'header `X-CSRF-Token` (letto dal cookie `ozon_csrf`).
5. Il frontend legge l'identità da `GET /get_session` — **mai token**.

`GET /get_session` espone solo:

```json
{
  "uid": "...",
  "username": "...",
  "authenticated": true,
  "app_code": "demo"
}
```

Token, refresh token e claim JWT raw non vengono esposti. I campi
`authtoken`/`authToken`/`auth_token` nel payload non sono credenziali: il
backend li rimuove prima del runtime action — il frontend non deve inviarli.

## Header identità trusted (deploy dietro reverse proxy trusted)

In modalità `AUTH_MODE=keycloak` dietro proxy trusted (es. oauth2-proxy), il
backend legge **un solo header**, quello configurato in
`KEYCLOAK_REMOTE_USER_HEADER` (`x-remote-user` di default):

- il backend non si fida degli header mandati dal client diretto — solo
  dell'header iniettato nel boundary del proxy;
- gli altri header della famiglia oauth2-proxy (`X-Forwarded-User`,
  `X-Auth-Request-User`, `X-Remote-Groups`, ...) **non** sono fidati
  automaticamente;
- il proxy pubblico deve azzerare l'intera famiglia prima di iniettare il
  solo header configurato — il trust dipende dal boundary di rete, non da una
  firma dell'header. Il nginx del web-client azzera tutta la famiglia e
  inoltra solo `x-remote-user` (verificato con test end-to-end).

## WebSocket

`/ws/actions` accetta il cookie di sessione (`AUTH_COOKIE_NAME`) e, per le
connessioni browser, applica il controllo `Origin`. Il bearer nel primo
messaggio `type=auth` resta riservato ai client non-browser; **i token in
query string non sono accettati**.

## `is_admin` e ruoli: non da Keycloak

Keycloak resta responsabile solo dell'autenticazione. `is_admin` e i ruoli
vengono dalla collection Mongo `group_users` (gruppi
`admin`/`user`/`operator`/`manager`/...), come descritto in
[ACL](acl.md). Nessun client role Keycloak è richiesto.

## `user` vs `people`

Per deployment con anagrafica esterna (`people`):

- **`people` come sorgente autoritativa**;
- **`user` come cache/read-model locale** usata dal backend a runtime;
- **sync schedulato** per gli aggiornamenti ordinari + refresh on-demand solo
  quando un utente autenticato non esiste ancora o è incompleto.

Questo tiene pulito il path di autenticazione: niente dipendenze sincrone da
sistemi esterni nel login. La creazione sessione legge sempre la collection
`user` locale e crea/aggiorna una `Session` `ozon-env` per coppia
`uid + app_code`.

## Punto di estensione

Il punto naturale da verticalizzare è `app/services/session_auth.py`:

- `_load_user_record(...)` per cambiare la strategia di risoluzione utente;
- `build_keycloak_session(...)` per arricchire in modo controllato il
  bootstrap della `Session`.

## Auth mode

| `AUTH_MODE` | Comportamento |
|---|---|
| `token` (storico) | `Authorization: Bearer <token>` usato direttamente come chiave di sessione |
| `keycloak` | login OIDC + sessione applicativa da cookie (la modalità usata dallo stack service-app) |