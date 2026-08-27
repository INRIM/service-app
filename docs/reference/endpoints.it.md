---
title: Endpoint API
description: Riferimento degli endpoint HTTP del backend — sessione, record, liste NDJSON, remote select, import.
---

# Riferimento: Endpoint API

Autenticazione: sessione via cookie (BFF) o `Authorization: Bearer <token>`.
Formato risposta standard: `ResponseObject`, tranne lo stream NDJSON e
`GET /get_session`.

## Sessione e modelli

| Endpoint | Scopo | Risposta |
|---|---|---|
| `GET /` | health/liveness | `{"status": "live"}` |
| `GET /get_session` | sessione corrente | `{"uid", "username", "authenticated", "app_code"}` (mai token) |
| `GET /models/distinct` | `rec_name` distinti dei component | `mode="list"`, `data = [modelli]` |
| `GET /record/{model}` | schema form del model | `mode="form"` |
| `GET /record/{model}/{rec_name}` | record puntuale (dati+schema) | `mode="form"`; `404` se assente |
| `POST /record/{model}/{rec_name}` | upsert del record | `mode="form"` |

## Liste: `POST /list/{model}`

Body `ListRequest`:

```json
{ "query": {}, "order": "", "skip": 0, "limit": 100 }
```

- `order` accetta `campo:asc|desc`, `-campo` (desc), `campo` (asc).
- Risposta **streaming** `application/x-ndjson`: primo pacchetto envelope
  (`content.data` vuoto), poi un record per riga.
- Header di risposta: `X-Order`, `X-Skip`, `X-Limit`, `X-columns`,
  `X-Total-Count` (totale match, non limitato alla pagina).

Le stesse regole di validazione (`query`/`order`) valgono per
`GET|POST /action/{name}` in `mode=list` e per
`POST /filter/fast_search/{action_name}` — vedi
[Query field ACL gate](../guides/query-field-acl.md).

## Remote select

| Endpoint | Logica |
|---|---|
| `POST /models/distinct` (dual-use) | `properties` vuote → lista modelli; `key`+`curr_model` → opzioni select |
| `POST /get_remote_data_select` / `POST /get_remote_select` | opzioni select via component (`key`+`curr_model`); `data.url` nel payload → `400` (rimosso, SSRF) |

Contratto completo: [Select remote](../guides/remote-select.md).

## Import

```
POST /import/{model}?take_ownership=false|true
```

Accetta `.xlsx`, `.xls`, `.csv`, `.json` (lato UI). Match su `rec_name`;
`id`/`_id` del payload scartati; ownership governata da `take_ownership` —
dettagli ed errori `403` in [Import e ownership](../guides/import-ownership.md).

## Action router

Riferimento dedicato: [Action router](action-router.md).

## WebSocket

| Endpoint | Auth |
|---|---|
| `/ws/actions` | cookie di sessione (`AUTH_COOKIE_NAME`) + controllo `Origin` per i browser; bearer nel primo messaggio `type=auth` solo per client non-browser; token in query string **non** accettati |

## Gateway Camunda

| Endpoint | Gate |
|---|---|
| avvio processo | `create` o `update` sul model del processo |
| complete task | `read` (model + record rule) prima di leggere il record |

Vedi [Worker e Camunda](../wizard/step-5-workers-camunda.md).

## Import/export lato frontend

Export XLS/CSV/JSON (completo o limitato al filtro corrente) e import con
anteprima, scelta autore e modalità reimport: disponibili agli
amministratori quando configurati per modello.