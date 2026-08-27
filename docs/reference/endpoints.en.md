---
title: API endpoints
description: Backend HTTP endpoint reference — session, records, NDJSON lists, remote select, import.
---

# Reference: API endpoints

Authentication: session via cookie (BFF) or `Authorization: Bearer <token>`.
Standard response format: `ResponseObject`, except for the NDJSON stream and
`GET /get_session`.

## Session and models

| Endpoint | Purpose | Response |
|---|---|---|
| `GET /` | health/liveness | `{"status": "live"}` |
| `GET /get_session` | current session | `{"uid", "username", "authenticated", "app_code"}` (never tokens) |
| `GET /models/distinct` | distinct component `rec_name`s | `mode="list"`, `data = [models]` |
| `GET /record/{model}` | model form schema | `mode="form"` |
| `GET /record/{model}/{rec_name}` | single record (data+schema) | `mode="form"`; `404` if missing |
| `POST /record/{model}/{rec_name}` | record upsert | `mode="form"` |

## Lists: `POST /list/{model}`

Body `ListRequest`:

```json
{ "query": {}, "order": "", "skip": 0, "limit": 100 }
```

- `order` accepts `field:asc|desc`, `-field` (desc), `field` (asc).
- Response is an **NDJSON stream** (`application/x-ndjson`): first packet is
  the envelope (`content.data` empty), then one record per line.
- Response headers: `X-Order`, `X-Skip`, `X-Limit`, `X-columns`,
  `X-Total-Count` (total matches, not limited to the page).

The same validation rules (`query`/`order`) apply to
`GET|POST /action/{name}` in `mode=list` and to
`POST /filter/fast_search/{action_name}` — see
[Query field ACL gate](../guides/query-field-acl.md).

## Remote select

| Endpoint | Logic |
|---|---|
| `POST /models/distinct` (dual-use) | empty `properties` → model list; `key`+`curr_model` → select options |
| `POST /get_remote_data_select` / `POST /get_remote_select` | select options via component (`key`+`curr_model`); `data.url` in payload → `400` (removed, SSRF) |

Full contract: [Remote selects](../guides/remote-select.md).

## Import

```
POST /import/{model}?take_ownership=false|true
```

Accepts `.xlsx`, `.xls`, `.csv`, `.json` (UI side). Matching on `rec_name`;
payload `id`/`_id` stripped; ownership governed by `take_ownership` —
details and `403` errors in [Import and ownership](../guides/import-ownership.md).

## Action router

Dedicated reference: [Action router](action-router.md).

## WebSocket

| Endpoint | Auth |
|---|---|
| `/ws/actions` | session cookie (`AUTH_COOKIE_NAME`) + `Origin` check for browsers; bearer in the first `type=auth` message for non-browser clients only; tokens in query strings **not** accepted |

## Camunda gateway

| Endpoint | Gate |
|---|---|
| process start | `create` or `update` on the process model |
| task completion | `read` (model + record rule) before reading the record |

See [Workers and Camunda](../wizard/step-5-workers-camunda.md).

## Frontend import/export

XLS/CSV/JSON export (full or limited to the current filter) and import with
preview, author choice and re-import mode: available to administrators when
configured per model.