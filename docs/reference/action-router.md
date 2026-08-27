---
title: Action router
description: Contratto completo dell'action router — ResponseObject, menu, card, layout, action e query dedicate.
---

# Riferimento: Action router

Prefix: `/action`. Auth: sessione (cookie) o `Authorization: Bearer <token>`.
Tutte le risposte usano l'`envelope` `ResponseObject`.

## Contratto base (`ResponseObject`)

```json
{
  "fail": false,
  "message": "",
  "content": {
    "mode": "menu|card|layout|form|list|list_stream|action|redirect",
    "data": {},
    "readable": true,
    "editable": true,
    "can_create": true,
    "model": "",
    "query": {},
    "obfucated_fields": [],
    "editable_fields": [],
    "schema": [],
    "rec_name": "",
    "fields": {},
    "columns": {},
    "filter_kyes": {},
    "batch_size": 0,
    "total_count": 0
  }
}
```

Regola client: fare sempre switch su `mode` (non sul path chiamato).

## Endpoint

```text
GET    /action/menu[/{parent}]
GET    /action/dashboard[/{parent}]
GET    /action/layout[/{name}]
GET    /action/next_action/{curr_action}[/{rec_name}]
GET    /action/{name}[/{rec_name}]
POST   /action/{name}[/{rec_name}]
DELETE /action/{name}/{rec_name}
```

Parametri query di `GET /action/{name}`: `query` (stringa JSON, default
`"{}"`), `order`, `skip`, `limit`. `422` se `query` non è JSON valido.

## Funzione dei campi action

- `model` determina collezione, dominio (`get_domain`) e conteggio `number`
  delle card; **non** inferire il model dal nome action.
- schema UI = `view_name` se valorizzato, altrimenti schema di `model`.
- Action lista: `list_query` + query runtime + filtri default
  (`deleted=0`, `active=true`); `order` runtime ha precedenza sull'ordine base.
- Action form: con `rec_name` carica il record; senza apre il contesto di
  creazione.

Metadati aggiunti in `response.fields` per `mode=form`/`list`:

```json
{
  "action_name": "",
  "action_model": "",
  "action_type": "",
  "component_type": "",
  "submit_action_name": "",
  "next_action_name": "",
  "cancel_button": true,
  "abandon_action_name": "",
  "action_sequence": {
    "current_action": "",
    "submit_action": "",
    "submit_next_action": "",
    "abandon_action": ""
  }
}
```

## Menu (`mode = "menu"`)

`data` è una lista di oggetti-gruppo, chiave dinamica = label del gruppo:

```json
{
  "mode": "menu",
  "data": [
    {
      "Vendite": [
        {
          "model": "ordine", "key": "ordini_list", "type": "button",
          "label": "Ordini", "leftIcon": "it-list",
          "btn_action_type": false, "action_type": "window",
          "url_action": "/action/ordini_list", "builder": false
        }
      ]
    }
  ]
}
```

- `url_action`: rotta da invocare (canonica; `content` solo fallback legacy).
- `btn_action_type`: metodo suggerito (`post` per save/copy/delete).

Query dedicata con defaults: `deleted = 0`, `active = true`, filtro `apps`
su `menu_group` per `app_code`.

## Dashboard (`mode = "card"`)

```json
{
  "mode": "card",
  "model": "action",
  "data": [
    {
      "model": "ordine", "group_id": "vendite", "title": "Vendite",
      "buttons": [
        { "model": "ordine", "icon": "it-list", "action_type": "window",
          "content": "/action/ordini_list", "label": "Ordini",
          "mode": "list", "number": 37 }
      ]
    }
  ]
}
```

`number` è valorizzato per i bottoni `mode=list`, calcolato dal backend con
`list_query` + default query + risoluzione placeholder `_user_<campo>` +
normalizzazione dominio. Può essere `0` per le action non-lista.

## Layout (`mode = "layout"`)

```json
{
  "mode": "layout",
  "data": {
    "layout": "main_layout",
    "schema": { "rec_name": "main_layout", "type": "layout", "components": [] },
    "menu": [{ "Vendite": [] }],
    "settings": { "module_name": "MCI", "version": "1.0.0",
                  "logo_img_url": "/static/logo.png" }
  }
}
```

`schema` per la composizione pagina, `menu` per la navigazione, `settings`
per branding (nome modulo, versione, logo — fallback su runtime config).

## `next_action`

`GET /action/next_action/{curr_action}[/{rec_name}]`: carica l'action
corrente, valida `next_action_name`; se esiste →
`mode = "redirect"`, `data.next_page = "/action/{next}[/{rec_name}]"`;
altrimenti `204 No Content`.

## Error handling

- `422` se `query` non è JSON valido;
- payload action non trovato: `mode = "action"` con `data.status = "error"`;
- `403` per ACL (model/field/record/action) — vedi
  [ACL](../guides/acl.md) e [Query field ACL gate](../guides/query-field-acl.md).

## Checklist client

- chiamare sempre con prefix `/action`;
- gestire il rendering tramite `mode`;
- per `mode=menu`: iterare i gruppi (chiavi dinamiche);
- per `mode=card`: renderizzare `data[].buttons[]`;
- usare `url_action`/`content` come destinazione;
- non assumere `number > 0`;
- per i bottoni form: submit = `fields.submit_action_name`, abbandona =
  `fields.abandon_action_name`.