---
title: Step 4 — External services
description: Service registry, companion services (mail-sender, calendar-scheduler, identity-manager), core webhooks and remote selects.
---

# External services

<ol class="wizard-steps">
  <li class="wizard-done">Create a form</li>
  <li class="wizard-done">Components</li>
  <li class="wizard-done">Actions and groups</li>
  <li class="wizard-current">External services</li>
  <li class="">Workers and Camunda</li>
</ol>

## Service registry

The service registry is a **function of the core application**, not a
separate service: it uses the `service_registry` and `service_registry_repo`
models and exposes APIs under `/services/registry`.

Every companion service (`mail-sender`, `calendar-scheduler`,
`identity-manager`, ...) has a `manifest.json` and a self-contained
`docker-compose.yml` under `services/<name>/`, attached to the external
`ozn-network` network. The registry knows how to build and start each
companion from its own compose when needed. The global image build only
produces `ozonapp.db` and `ozonapp.app`.

Companions communicate with the backend in two ways:

- **client_credentials (M2M)** — the `calendar-scheduler` calls the backend
  `/client/run/calendar_tasks/*` endpoints with a Keycloak
  `serviceAccountsEnabled` client. Its service account
  (`service-account-calendar-scheduler`) must be in the `admin` group in
  `group_users`, otherwise the ACL denies the writes. An **audience mapper**
  is needed on both the web client and the M2M client: both tokens carry the
  `app_code` in the `aud` claim (`OZON_TOKEN_AUDIENCE` /
  `SCHEDULER_OAUTH_AUDIENCE`).
- **via `ozon-env`** — companions use
  [`ozon-env`](https://github.com/archetipo/ozon-env) as their base and
  access data with the same conventions as the workers (no HTTP calls to the
  core for data).

## Core webhooks

The backend can call external services to integrate ACL, user management and
synchronization logic **without moving data ownership** out of the core.
Configuration:

```bash
CORE_WEBHOOKS_ENABLED=true
CORE_WEBHOOKS_JSON='[{"url":"http://acl-service:8000/webhooks","events":["data.before_write","user.before_create"]}]'
CORE_WEBHOOKS_FAIL_MODE=open
CORE_WEBHOOKS_TIMEOUT_SECONDS=5
CORE_WEBHOOKS_SIGNING_SECRET=...
```

Supported events:

| Event | When | What the receiver can do |
|---|---|---|
| `data.before_write` | before local ACL and upsert | deny with `{"allow": false}` or rewrite the payload with `{"payload": {...}}` |
| `data.after_write` | after upsert | observe |
| `data.after_read` / `data.after_list` | after read | observe |
| `user.before_create` / `user.after_create` | user creation | deny / observe |
| `user.session.persist` | after session persistence | observe |
| `calendar.task.completed` / `calendar.task.failed` | after a calendar task run | outcome notification (fail-safe: a webhook error never blocks the run) |

`events` matching is exact (or `*` for all); for the calendar family list
both events.

## Remote selects against external URLs

A select can take its options from an external service. Definitions (URL,
path, headers, tokens) live **on the component**, server-side:

- the client sends `POST /get_remote_select` with `key` + `curr_model`;
- the backend resolves the remote endpoint from the component
  (`_load_remote_url_source`) and adds the configured headers;
- header values can come from `global_params`.

> Security: the branch accepting `data.url` from the payload was **removed**
> (2026-07 audit) — it was an SSRF and allowed exfiltrating `global_params`
> as HTTP headers to a client-chosen host. Clients must always pass
> `key` + `curr_model`. Contract in
> [Remote selects](../guides/remote-select.md).

## Example: a vertical service

Pattern for adding a service that extends the core:

1. Create `services/<name>/` with a self-contained `manifest.json` +
   `docker-compose.yml` on the `ozn-network` network.
2. Register in the service registry (or use webhooks for core events).
3. If the service must write data over HTTP (not via the DB), use a Keycloak
   M2M client and put its service account in the right group in
   `group_users`.

## Next step

Long-running, multi-actor processes: **Camunda 8** and workers.
[Step 5 — Workers and Camunda](step-5-workers-camunda.md).