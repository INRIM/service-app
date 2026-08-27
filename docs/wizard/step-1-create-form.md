---
title: Step 1 — Creare un form
description: Come si crea un form in service-app — builder drag&drop, plugin su /plugins, component e card in dashboard.
---

# Creare un form

<ol class="wizard-steps">
  <li class="wizard-current">Creare un form</li>
  <li class="">I componenti</li>
  <li class="">Le action e i gruppi</li>
  <li class="">Servizi esterni</li>
  <li class="">Worker e Camunda</li>
</ol>

Un "form" in service-app è un **component**: uno schema Form.io salvato nella
collection Mongo `component`, da cui il backend genera un **model** runtime
(collezione, campi, validazioni Pydantic). Attorno al component il backend
genera le azioni per listarla, aprirla e salvarla, e la card in dashboard.

## Strada A — il builder (drag&drop)

1. Entra con un utente del gruppo `admin` e attiva il **Builder** dal menu
   utente: i menu e le action amministrative diventano visibili.
2. Apri una form esistente e clicca **Modifica form** (il viewer non passa in
   builder se non con un'azione esplicita).
3. Trascina i campi nello schema Form.io (builder formio.js), configura
   etichette, validazioni, logica e proprietà.
4. Nel salvataggio attiva `create_menu_dashboard`: il backend genera da solo
   - un `menu_group` con `rec_name` = nome del model;
   - le **6 action di default** clonate dai template `sys` del plugin base:
     `list_` (menu/list), `new_` (window/form), `form_form_` (window/form),
     `submit_` (save), `copy_`, `delete_` — tutte sul tuo model.

Rifare il salvataggio dal builder **aggiorna** gli stessi record, non li
duplica.

> Il builder è una funzione amministrativa: chi può scrivere uno schema di
> form ottiene esecuzione JS nel browser di chi lo apre (la logica dei form
> Form.io è JavaScript). Va trattato come privilegio admin.

## Strada B — il plugin (infrastructure as data)

Niente UI: una cartella montata in `/plugins/<nome>/` con manifest, schema e
seed. La demo ([`inrim-forms-demo`](https://github.com/INRIM/inrim-forms-demo))
fa esattamente questo:

```
demo/plugin/
├── config.json               # manifest
├── schema/components.json    # la form "Modulo Dati Persona"
└── data/
    ├── menu_group.json       # card dashboard
    └── action.json           # le 6 action di default
```

Il manifest minimo:

```json
{
  "module_name": "demo",
  "schema": "/schema/components.json",
  "datas": [
    { "menu_group": "/data/menu_group.json" },
    { "action": "/data/action.json" }
  ],
  "depends": []
}
```

All'avvio il backend scopre i plugin in `/plugins/<nome>/`, upserta lo schema
nella collection `component` e i seed (`datas`) per `rec_name`.

I seed **riproducono** il risultato della strada A, così la card compare già
al primo avvio. Dettagli che contano (se li sbagli, la card sparisce):

- la card nasce dal `menu_group`, ma compare solo se **almeno una action non
  `sys`** punta a quel `menu_group`;
- i bottoni della card arrivano solo dalle action con `component_type` in
  `form`/`resource`/`layout`;
- `admin: false` e `parent: ""` sul `menu_group`, altrimenti finisce nel menu
  admin o in una card-cartella;
- `apps: ["<app_code>"]` fa lo scoping multi-tenant;
- configura `groups` per rendere la card visibile ai gruppi giusti.

## Lo schema del component: che aspetto ha

Un component porta lo schema Form.io (array `components`) più le proprietà
applicative Ozon in `properties` — che sono anche la config dell'ACL:

```json
{
  "rec_name": "modulo_dati_persona",
  "title": "Modulo Dati Persona",
  "type": "resource",
  "display": "form",
  "authenticate": true,
  "components": [
    { "label": "Name", "key": "rec_name", "type": "textfield", "input": true },
    { "label": "Label", "key": "label", "type": "textfield", "input": true }
  ],
  "properties": {
    "rheader": "1",
    "rfooter": "1",
    "models_groups": { "rules": [] },
    "models_restricted_fields": {}
  }
}
```

Ogni campo ha:

| Proprietà | Significato |
|---|---|
| `key` | nome del campo (dot path annidato, es. `address.city`) |
| `type` | tipo Form.io (`textfield`, `select`, `textarea`, `columns`, ...) |
| `properties` | proprietà applicative Ozon (ACL, remote select, tabelle, ...) |
| `logic` | condizioni JSON Logic (trigger → azioni) |

## Verifica

1. Riavvia lo stack (i plugin vengono installati all'avvio) o salva dal
   builder.
2. Apri `http://localhost:4200`: la card del form è in dashboard, senza
   passare dal builder.
3. Compila e salva: i dati finiscono nella collezione Mongo omonima del
   component, via `POST /action/submit_<model>`.

## Prossimo step

Ora che il form esiste, vediamo **quelli che lo compongono**:
[Step 2 — I componenti e le funzionalità](step-2-components.md).