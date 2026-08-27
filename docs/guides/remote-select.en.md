---
title: Remote selects
description: The remote select contract — RemoteSelectRequest, internal and external sources, response normalization.
---

# Remote selects

Selects can take their options from an internal model or a remote URL.
Endpoints:

- `POST /get_remote_data_select` (and alias `POST /get_remote_select`)
- `POST /models/distinct` (dual-use: model list or select options)

## The contract

Canonical `RemoteSelectRequest` payload:

```json
{
  "key": "string",
  "curr_model": "string",
  "data": {
    "url": "string",
    "pathValue": "string",
    "headers": [{ "key": "string", "value": "string" }],
    "headerKey": "string",
    "headerValueKey": "string"
  },
  "properties": {
    "model": "string",
    "domain": {},
    "compute_label": "string",
    "src": "string",
    "label": "string",
    "id": "string"
  }
}
```

### 1) Internal FormIO source (`key + curr_model`)

Used when the select does not point to an absolute URL. The client sends
`key` + `curr_model`; the backend uses the component's FormIO configuration
(`properties`: `model`, `domain`, `label`, `id`, `compute_label`).

```json
{
  "key": "implied_groups",
  "curr_model": "groups",
  "data": {},
  "properties": { "src": "url", "model": "groups",
                  "id": "rec_name", "label": "label" }
}
```

### 2) Remote URL source — server-side only

URL, path, header and token definitions live **on the component
definition**, not in the payload. The backend resolves the remote endpoint
(`_load_remote_url_source`) and adds the configured headers; header values
can come from `global_params`.

> **Breaking change (2026-07 security audit).** The branch accepting
> `data.url` from the body was removed: it was an SSRF (arbitrary URL fetched
> by the server with the response returned to the caller) and
> `headerValueKey` ended up in `get_global_param()` — which applies no ACL —
> allowing any `global_params` record value to be sent as an HTTP header to a
> client-chosen host. Clients must always pass `key` + `curr_model`.

If `data.url` is present without `key`/`curr_model`: **400**.

## Branch selection logic

- empty `properties` → model list (`get_models`);
- meaningful `properties` but no `key`/`curr_model` → fallback to model list;
- `key` + `curr_model` present → select options from `get_select_options`;
- `data.url` without `key`/`curr_model` → `400` (see breaking change above).

## Response normalization (frontend)

The frontend normalizes the backend response variants:

- `content.data`, `data.items`, `data.records`, `data.values`;
- `{ label, value }`, `{ k, v }` items, fallback `{ id/name/title/... }`.

Internal result: a uniform `{ label, value }` array.

## Frontend behavior

- Cache and de-duplication of concurrent requests.
- Initial hydration and updates of dependent selects.
- Readable label rendering in table cells too.
- Dedicated read-only styling for Choices.js selects.
- Remote selects in fast-search forms hydrate through the same
  infrastructure as normal forms.