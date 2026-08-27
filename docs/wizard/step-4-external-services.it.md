---
title: Step 4 — I servizi esterni
description: Service registry, companion service (mail-sender, calendar-scheduler, identity-manager), core webhooks e select remote.
---

# I servizi esterni

<ol class="wizard-steps">
  <li class="wizard-done">Creare un form</li>
  <li class="wizard-done">I componenti</li>
  <li class="wizard-done">Le action e i gruppi</li>
  <li class="wizard-current">Servizi esterni</li>
  <li class="">Worker e Camunda</li>
</ol>

## Service registry

Il registro dei servizi è una **funzione del core applicativo**, non un
servizio separato: usa i modelli `service_registry` e `service_registry_repo`
ed espone API sotto `/services/registry`.

Ogni companion service (`mail-sender`, `calendar-scheduler`,
`identity-manager`, ...) ha un `manifest.json` e un `docker-compose.yml`
autonomo sotto `services/<name>/`, collegato alla rete esterna `ozn-network`.
Il registry sa come buildare e avviare ogni companion dal suo compose quando
serve. Il build globale dell'immagine crea solo `ozonapp.db` e `ozonapp.app`.

I companion comunicano col backend in due modi:

- **client_credentials (M2M)** — il `calendar-scheduler` chiama gli endpoint
  `/client/run/calendar_tasks/*` del backend con un client Keycloak
  `serviceAccountsEnabled`. Il suo service account
  (`service-account-calendar-scheduler`) deve stare nel gruppo `admin` in
  `group_users`, altrimenti l'ACL nega le scritture. Serve un **audience
  mapper** sia sul client web sia sul client M2M: entrambi i token contengono
  l'`app_code` nel claim `aud` (`OZON_TOKEN_AUDIENCE` / `SCHEDULER_OAUTH_AUDIENCE`).
- **via `ozon-env`** — i companion usano [`ozon-env`](https://github.com/archetipo/ozon-env)
  come base e accedono ai dati con le stesse convenzioni dei worker (niente
  chiamate HTTP al core per i dati).

## Core webhooks

Il backend può chiamare servizi esterni per integrare logiche di ACL, gestione
utenti e sincronizzazioni **senza spostare la competenza dei dati** fuori dal
core. Configurazione:

```bash
CORE_WEBHOOKS_ENABLED=true
CORE_WEBHOOKS_JSON='[{"url":"http://acl-service:8000/webhooks","events":["data.before_write","user.before_create"]}]'
CORE_WEBHOOKS_FAIL_MODE=open
CORE_WEBHOOKS_TIMEOUT_SECONDS=5
CORE_WEBHOOKS_SIGNING_SECRET=...
```

Eventi supportati:

| Evento | Quando | Cosa può fare il receiver |
|---|---|---|
| `data.before_write` | prima di ACL locale e upsert | negare con `{"allow": false}` o riscrivere il payload con `{"payload": {...}}` |
| `data.after_write` | dopo upsert | osservare |
| `data.after_read` / `data.after_list` | dopo lettura | osservare |
| `user.before_create` / `user.after_create` | creazione utente | negare / osservare |
| `user.session.persist` | dopo persistenza sessione | osservare |
| `calendar.task.completed` / `calendar.task.failed` | post-run di un calendar task | notifica di esito (fail-safe: un errore della webhook non blocca mai la run) |

Il match degli `events` è esatto (o `*` per tutti); per la famiglia calendar
elencare entrambi gli eventi.

## Select remote verso URL esterni

Un select può prendere le opzioni da un servizio esterno. Le definizioni
(url, path, header, token) vivono **sul component**, server-side:

- il client invia `POST /get_remote_select` con `key` + `curr_model`;
- il backend risolve l'endpoint remoto dal component
  (`_load_remote_url_source`) e aggiunge gli header configurati;
- i valori degli header possono venire dai `global_params`.

> Sicurezza: il ramo che accettava `data.url` dal payload è stato **rimosso**
> (audit 2026-07) — era una SSRF e consentiva di esfiltrare `global_params`
> come header HTTP verso un host scelto dal client. I client devono passare
> sempre `key` + `curr_model`. Contratto in
> [Select remote](../guides/remote-select.md).

## Esempio: un servizio verticale

Pattern per aggiungere un servizio che estende il core:

1. Crea `services/<name>/` con `manifest.json` + `docker-compose.yml`
   autonomo sulla rete `ozn-network`.
2. Registrati nel service registry (o usa i webhooks per gli eventi core).
3. Se il servizio deve scrivere dati via HTTP (non via DB), usa un client
   M2M Keycloak e metti il suo service account nel gruppo giusto in
   `group_users`.

## Prossimo step

I processi lunghi e multi-attore: **Camunda 8** e i worker.
[Step 5 — I worker e Camunda](step-5-workers-camunda.md).