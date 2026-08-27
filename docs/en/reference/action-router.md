---
title: Action router
description: Full action router contract — ResponseObject, menu, cards, layout, actions and dedicated queries.
---

# Reference: Action router

Prefix: `/action`. Auth: session (cookie) or `Authorization: Bearer <token>`.
All responses use the `ResponseObject` envelope.

## Base contract (`ResponseObject`)

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

Client rule: always switch on `mode` (never on the called path).

## Endpoints

```text
GET    /action/menu[/{parent}]
GET    /action/dashboard[/{parent}]
GET    /action/layout[/{name}]
GET    /action/next_action/{curr_action}[/{rec_name}]
GET    /action/{name}[/{rec_name}]
POST   /action/{name}[/{rec_name}]
DELETE /action/{name}/{rec_name}
```

Query parameters of `GET /action/{name}`: `query` (JSON string, default
`"{}"`), `order`, `skip`, `limit`. `422` if `query` is not valid JSON.

## Action field semantics

- `model` determines the collection, the domain (`get_domain`) and the card
  `number` count; **do not** infer the model from the action name.
- UI schema = `view_name` when set, otherwise the `model` schema.
- List actions: `list_query` + runtime query + default filters
  (`deleted=0`, `active=true`); runtime `order` takes precedence over the
  base sort.
- Form actions: with `rec_name` loads the record; without opens the creation
  context.

Metadata added in `response.fields` for `mode=form`/`list`:

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

`data` is a list of group objects, dynamic key = group label:

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

- `url_action`: route to invoke (canonical; `content` is a legacy fallback
  only).
- `btn_action_type`: suggested method (`post` for save/copy/delete).

Dedicated query defaults: `deleted = 0`, `active = true`, `apps` filter on
`menu_group` by `app_code`.

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

`number` is populated for `mode=list` buttons, computed by the backend from
`list_query` + default query + `_user_<field>` placeholder resolution +
domain normalization. It can be `0` for non-list actions.

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

`schema` for page composition, `menu` for navigation, `settings` for branding
(module name, version, logo — fallback to runtime config).

## `next_action`

`GET /action/next_action/{curr_action}[/{rec_name}]`: loads the current
action, validates `next_action_name`; if it exists →
`mode = "redirect"`, `data.next_page = "/action/{next}[/{rec_name}]"`;
otherwise `204 No Content`.

## Error handling

- `422` if `query` is not valid JSON;
- action payload not found: `mode = "action"` with `data.status = "error"`;
- `403` for ACL (model/field/record/action) — see
  [ACL](../guides/acl.md) and [Query field ACL gate](../guides/query-field-acl.md).

## Client checklist

- always call with the `/action` prefix;
- drive rendering from `mode`;
- for `mode=menu`: iterate the groups (dynamic keys);
- for `mode=card`: render `data[].buttons[]`;
- use `url_action`/`content` as the destination;
- never assume `number > 0`;
- for form buttons: submit = `fields.submit_action_name`, abandon =
  `fields.abandon_action_name`.