---
title: Step 2 — Components and features
description: The components available in service-app forms — Form.io fields, custom Ozon components, logic, remote selects, files.
---

# Components and features

<ol class="wizard-steps">
  <li class="wizard-done">Create a form</li>
  <li class="wizard-current">Components</li>
  <li class="">Actions and groups</li>
  <li class="">External services</li>
  <li class="">Workers and Camunda</li>
</ol>

The form schema is standard Form.io: the frontend interprets the backend
contract and dynamically adapts interface, actions and permissions — there is
no rigid per-model configuration. On top of the standard components, backend
and frontend add their own features.

## Basic Form.io components

- Layout: `columns`, `panel`, `well`, `tabs`, `fieldset`, `datagrid`,
  `container` — traversed recursively by the frontend (default values are
  inserted without overwriting real values).
- Input: `textfield`, `textarea`, `select`, `number`, `checkbox`, `radio`,
  `datetime`, `file`, `button`, ...
- **Form.io validation** runs before POST actions: errors block submission
  and are shown to the user.
- **Logic** (`logic`) uses JSON Logic: a trigger (condition) → one or more
  actions (show/hide, enable/disable, compute a value). Real example from the
  demo "groups" form — the "Elimina" button hides for non-admins:

  ```json
  {
    "name": "delete active",
    "trigger": { "type": "json", "json": { "!": [{ "and": [
      { "var": ["data.rec_name", false] },
      { "var": ["user.is_admin", false] }
    ] } }] },
    "actions": [{ "name": "activate button", "type": "property",
                  "property": { "label": "Hidden", "value": "hidden",
                                "type": "boolean" }, "state": true }]
  }
  ```

## Remote selects

A `select` can take its options from an **internal model** or a **remote
URL**, resolved server-side from the component. The config lives in the
component's `properties`:

```json
{
  "label": "Gruppi implicati di default",
  "key": "implied_groups",
  "type": "select",
  "multiple": true,
  "dataSrc": "url",
  "data": { "url": "/models/distinct" },
  "properties": {
    "id": "rec_name",
    "label": "label",
    "domain": "{}",
    "model": "groups",
    "compute_label": "label"
  }
}
```

The frontend calls `POST /get_remote_select` with `key` + `curr_model`: URL,
headers and tokens live **on the component definition**, never in the payload
(full contract in [Remote selects](../guides/remote-select.md)).

## Custom Ozon components

| Component | What it does |
|---|---|
| `ozon_data_table` | Ozon list embedded in a Form.io form: runs a list action independent of the main list, combines the parent record context with the query (JSON Logic), can open/save records in a modal and reload itself after saving |
| JSON editor | based on `vanilla-jsoneditor` — enabled with `properties.jeditor: "y"` on `textarea`/JSON fields |
| WYSIWYG editor | based on Quill, sanitized HTML (DOMPurify) |
| File/attachments | dedicated template for Ozon attachments, authenticated download delegated to the API client |
| `table` | record table inside the form (actions on a related collection) |
| `search_area` | search/query area configured per model (query builder) |

The field→Python type mapping is done by the backend `ModelMaker` reading the
field `type`: `textarea` → `str`, a field with `properties.type: "json"` →
`dict`, `select multiple` → `List[Any]`. The generated types must match what
Mongo actually contains (for details see
[ACL](../guides/acl.md)).

## What the form receives from the backend

Every action response carries metadata that drives the UI:

```json
{
  "content": {
    "mode": "form",
    "data": {},
    "readable": true,
    "editable": true,
    "can_create": true,
    "model": "modulo_dati_persona",
    "schema": {},
    "rec_name": "",
    "fields": {},
    "columns": {},
    "context_actions": []
  }
}
```

- `mode` picks the renderer (`list`, `form`, `card`, `menu`, `layout`, ...).
- `editable AND can_create` decide read-only: if even one is `false` the
  viewer gets `readOnly: true` and the mutating actions disappear.
- `fields.submit_action_name` / `fields.abandon_action_name` tell the
  frontend which action to run on Save/Abandon.
- `obfucated_fields` / `editable_fields` inform about which fields the user
  sees in clear and can modify.

## Lists and tables

- Desktop lists use **AG Grid**; on mobile rows become responsive cards.
- Full JSON loading or **NDJSON** stream (`application/x-ndjson`) with
  counters.
- Query builder with `AND`/`OR` rules, field-type-aware operators and a
  preview of the generated MongoDB query.
- Fast search (`fields.fast_search`) and quick actions (`fields.fast_actions`)
  on multi-selection.
- Import/export XLS/CSV/JSON for administrators, with ownership handling (see
  [Import and ownership](../guides/import-ownership.md)).

## Next step

Forms alone don't make an app: you need the **actions** that open, save and
navigate them. [Step 3 — Actions and groups](step-3-actions.md).