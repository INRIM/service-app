---
title: Keycloak and session
description: How authentication works in service-app — Keycloak OIDC, BFF pattern, session cookies, authentication/authorization separation.
---

# Keycloak and application session

## Separation of responsibilities

- **Keycloak** handles authentication and SSO (OIDC).
- **The backend** (`ozon-env-app`) generates and owns the application session.
- **The frontend** never builds or forges identity: it contains no secrets and
  handles no tokens.

The session model remains the canonical `ozon-env` one
(`ozonenv.core.BaseModels.Session`); the backend defines no alternative
session model.

## The flow (BFF pattern)

1. `/login` redirects the browser to Keycloak (Authorization Code).
2. `/auth/callback` exchanges the code, creates the application session and
   resets the `ozon_session` (httponly) + `ozon_csrf` cookies.
3. The web-client (nginx) is the single-origin reverse proxy for
   `/api/*`, `/login`, `/logout`, `/auth/*` — no CORS, simple cookies.
4. Authenticated requests travel with the cookie; mutating calls add the
   `X-CSRF-Token` header (read from the `ozon_csrf` cookie).
5. The frontend reads identity from `GET /get_session` — **never tokens**.

`GET /get_session` exposes only:

```json
{
  "uid": "...",
  "username": "...",
  "authenticated": true,
  "app_code": "demo"
}
```

Tokens, refresh tokens and raw JWT claims are never exposed. The
`authtoken`/`authToken`/`auth_token` payload fields are not credentials: the
backend strips them before the action runtime — the frontend must not send
them.

## Trusted identity header (behind a trusted reverse proxy)

In `AUTH_MODE=keycloak` mode behind a trusted proxy (e.g. oauth2-proxy), the
backend reads **one header only**, the one configured in
`KEYCLOAK_REMOTE_USER_HEADER` (`x-remote-user` by default):

- the backend does not trust headers sent by the direct client — only the
  header injected inside the proxy boundary;
- the other oauth2-proxy family headers (`X-Forwarded-User`,
  `X-Auth-Request-User`, `X-Remote-Groups`, ...) are **not** trusted
  automatically;
- the public proxy must blank the whole family before injecting the one
  configured header — trust depends on the network boundary, not on a header
  signature. The web-client nginx blanks the whole family and forwards only
  `x-remote-user` (verified with an end-to-end test).

## WebSocket

`/ws/actions` accepts the session cookie (`AUTH_COOKIE_NAME`) and, for
browser connections, applies the `Origin` check. The bearer in the first
`type=auth` message stays reserved for non-browser clients; **tokens in query
strings are not accepted**.

## `is_admin` and roles: not from Keycloak

Keycloak stays responsible for authentication only. `is_admin` and roles come
from the Mongo `group_users` collection (`admin`/`user`/`operator`/`manager`/
... groups), as described in [ACL](acl.md). No Keycloak client role is
required.

## `user` vs `people`

For deployments with an external registry (`people`):

- **`people` as the authoritative source**;
- **`user` as the local cache/read-model** used by the backend at runtime;
- **scheduled sync** for ordinary updates + on-demand refresh only when an
  authenticated user does not exist yet or is clearly incomplete.

This keeps the authentication path clean: no synchronous dependency on
external systems in login. Session creation always reads the local `user`
collection and creates/updates an `ozon-env` `Session` for the
`uid + app_code` pair.

## Extension point

The natural place to verticalize is `app/services/session_auth.py`:

- `_load_user_record(...)` to change the user resolution strategy;
- `build_keycloak_session(...)` to enrich the `Session` bootstrap in a
  controlled way.

## Auth modes

| `AUTH_MODE` | Behavior |
|---|---|
| `token` (historical) | `Authorization: Bearer <token>` used directly as session key |
| `keycloak` | OIDC login + application session from cookie (the mode used by the service-app stack) |