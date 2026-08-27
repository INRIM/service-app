---
title: Step 1 — Create a form
description: How to create a form in service-app — drag&drop builder, plugin on /plugins, component and dashboard card.
---

# Create a form

<ol class="wizard-steps">
  <li class="wizard-current">Create a form</li>
  <li class="">Components</li>
  <li class="">Actions and groups</li>
  <li class="">External services</li>
  <li class="">Workers and Camunda</li>
</ol>

A "form" in service-app is a **component**: a Form.io schema saved in the
Mongo `component` collection, from which the backend generates a runtime
**model** (collection, fields, Pydantic validations). Around the component
the backend generates the actions to list, open and save it, and the
dashboard card.

## Path A — the builder (drag&drop)

1. Log in with a user in the `admin` group and enable the **Builder** from
   the user menu: administrative menus and actions become visible.
2. Open an existing form and click **Modifica form** (the viewer never enters
   builder mode without an explicit action).
3. Drag fields into the Form.io schema (formio.js builder), configure labels,
   validations, logic and properties.
4. On save, enable `create_menu_dashboard`: the backend generates
   - a `menu_group` with `rec_name` = model name;
   - the **6 default actions** cloned from the `sys` templates of the base
     plugin: `list_` (menu/list), `new_` (window/form), `form_form_`
     (window/form), `submit_` (save), `copy_`, `delete_` — all on your model.

Saving again from the builder **updates** the same records, it does not
duplicate them.

> The builder is an administrative feature: whoever can write a form schema
> gets JS execution in the browser of whoever opens it (Form.io form logic is
> JavaScript). Treat it as an admin privilege.

## Path B — the plugin (infrastructure as data)

No UI needed: a folder mounted at `/plugins/<name>/` with manifest, schema
and seeds. The demo
([`inrim-forms-demo`](https://github.com/INRIM/inrim-forms-demo)) does
exactly this:

```
demo/plugin/
├── config.json               # manifest
├── schema/components.json    # the "Modulo Dati Persona" form
└── data/
    ├── menu_group.json       # dashboard card
    └── action.json           # the 6 default actions
```

The minimal manifest:

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

At startup the backend discovers plugins under `/plugins/<name>/`, upserts
the schema into the `component` collection and the seeds (`datas`) by
`rec_name`.

The seeds **reproduce** the result of path A, so the card appears on first
startup. Details that matter (if you get them wrong, the card disappears):

- the card is born from the `menu_group`, but only shows if **at least one
  non-`sys` action** points to that `menu_group`;
- card buttons come only from actions with `component_type` in
  `form`/`resource`/`layout`;
- `admin: false` and `parent: ""` on the `menu_group`, otherwise it ends up
  in the admin menu or in a card-folder;
- `apps: ["<app_code>"]` provides multi-tenant scoping;
- configure `groups` to make the card visible to the right groups.

## The component schema: what it looks like

A component carries the Form.io schema (`components` array) plus the Ozon
application properties in `properties` — which are also the ACL config:

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

Every field has:

| Property | Meaning |
|---|---|
| `key` | field name (nested dot path, e.g. `address.city`) |
| `type` | Form.io type (`textfield`, `select`, `textarea`, `columns`, ...) |
| `properties` | Ozon application properties (ACL, remote select, tables, ...) |
| `logic` | JSON Logic conditions (trigger → actions) |

## Verify

1. Restart the stack (plugins are installed at startup) or save from the
   builder.
2. Open `http://localhost:4200`: the form card is in the dashboard, without
   going through the builder.
3. Fill it in and save: data lands in the Mongo collection named after the
   component, via `POST /action/submit_<model>`.

## Next step

Now that the form exists, let's look at **what it is made of**:
[Step 2 — Components and features](step-2-components.md).