---
title: Select remote
description: Il contratto delle select remote — RemoteSelectRequest, sorgenti interne ed esterne, normalizzazione delle risposte.
---

# Select remote

Le select possono prendere le opzioni da un model interno o da un URL
remoto. Endpoint:

- `POST /get_remote_data_select` (e alias `POST /get_remote_select`)
- `POST /models/distinct` (dual-use: lista modelli o opzioni select)

## Il contratto

Payload canonico `RemoteSelectRequest`:

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

### 1) Sorgente interna FormIO (`key + curr_model`)

Usata quando il select non punta a un URL assoluto. Il client invia `key` +
`curr_model`; il backend usa la configurazione FormIO del component
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

### 2) Sorgente URL remota — solo server-side

Le definizioni di URL, path, header e token vivono **sulla definizione del
component**, non nel payload. Il backend risolve l'endpoint remoto
(`_load_remote_url_source`) e aggiunge gli header configurati; i valori degli
header possono venire dai `global_params`.

> **Breaking change (audit sicurezza 2026-07).** Il ramo che accettava
> `data.url` dal body è stato rimosso: era una SSRF (URL arbitrario fetchato
> dal server con la risposta restituita al chiamante) e `headerValueKey`
> finiva in `get_global_param()` — senza ACL — permettendo di spedire il
> valore di qualunque record `global_params` come header HTTP verso un host
> scelto dal client. I client devono passare sempre `key` + `curr_model`.

Se è presente `data.url` senza `key`/`curr_model`: **400**.

## Logica di selezione del ramo

- `properties` vuote → lista modelli (`get_models`);
- `properties` significative ma senza `key`/`curr_model` → fallback lista
  modelli;
- `key` + `curr_model` presenti → opzioni select da `get_select_options`;
- `data.url` senza `key`/`curr_model` → `400` (vedi breaking change sopra).

## Normalizzazione risposta (frontend)

Il frontend normalizza le varianti di risposta backend:

- `content.data`, `data.items`, `data.records`, `data.values`;
- elementi `{ label, value }`, `{ k, v }`, fallback `{ id/name/title/... }`.

Risultato interno: array uniforme `{ label, value }`.

## Comportamento frontend

- Cache e deduplicazione delle richieste concorrenti.
- Idratazione iniziale e aggiornamento delle select dipendenti.
- Rendering leggibile delle etichette anche nelle celle tabella.
- Stile readonly dedicato per le select Choices.js.
- Le select remote dei form di ricerca veloce vengono idratate con la stessa
  infrastruttura dei form normali.