---
title: Step 3 — Actions and groups
description: Action router, menu, dashboard, default actions and ACL groups — how the backend drives navigation and permissions.
---

# Actions and groups

<ol class="wizard-steps">
  <li class="wizard-done">Create a form</li>
  <li class="wizard-done">Components</li>
  <li class="wizard-current">Actions and groups</li>
  <li class="">External services</li>
  <li class="">Workers and Camunda</li>
</ol>

Everything the user sees and does goes through the **action router**
(`/action/...`). An **action** is a record in the `action` collection: the
client does not hardcode logic for specific endpoints — it reads the action
metadata and reacts.

## The action as a record

Relevant fields:

| Field | Meaning |
|---|---|
| `rec_name` | action identifier (becomes `{name}` in `/action/{name}`) |
| `model` | business target model — determines which collection is read/written |
| `view_name` | optional override of the **UI schema** (not the data model) |
| `mode` | expected output (`list`, `form`, ...) |
| `action_type` | semantics: `menu`, `window`, `process_task`, `save`, `copy`, `delete` |
| `component_type` | for actions on components: `form`, `resource`, `layout` |
| `list_query` | base filter for list actions |
| `groups` | ACL groups that can see/open the action |
| `title`, `button_icon` | rendering |
| `url_action` | route to invoke (canonical for menu buttons) |
| `builder_enabled` | flag for the builder UI |

The `model` is the center of behavior: it determines the collection, the
effective domain (`get_domain`) and the `number` count of cards. The UI
schema comes from `view_name` when set, otherwise from `model` — so
`list_doc_beni_servizi` can read from `model=documento` while using the
`documento_beni_servizi` schema.

## The 6 default actions

When you create a form (builder or plugin), the backend generates:

| Action | mode | action_type | Purpose |
|---|---|---|---|
| `list_<model>` | list | window | list/table |
| `new_<model>` | form | menu | new record (via `next_action`) |
| `form_form_<model>` | form | window | detail form (create/edit) |
| `submit_<model>` | — | save | saving (form submit) |
| `copy_<model>` | — | copy | duplicate record |
| `delete_<model>` | — | delete | soft delete |

Naming can change per project: the client must rely on
`fields.submit_action_name`, `fields.abandon_action_name` and `mode`, not on
the name.

## Action router endpoints

```text
GET  /action/menu[/{parent}]        menu grouped by menu_group
GET  /action/dashboard[/{parent}]   dashboard cards (mode=card)
GET  /action/layout[/{name}]        UI bootstrap (schema+menu+settings)
GET  /action/next_action/{curr}[/{rec_name}]   next step (redirect)
GET|POST|DELETE /action/{name}[/{rec_name}]   action execution
```

All responses share the `ResponseObject` envelope: the client switches on
`content.mode`, never on the called path. Full contract in
[Action router reference](../reference/action-router.md).

Typical client flow:

1. `GET /action/layout` → schema, menu, branding (`settings`).
2. `GET /action/dashboard` → cards (each button carries `number` = count of
   list records, computed by the backend with `list_query` + ACL).
3. Click on an action → `GET /action/{name}` → render by `mode`.
4. Save → `POST /action/{name}[/{rec_name}]` (or `submit_action_name`).
5. Delete → `DELETE /action/{name}/{rec_name}` (soft delete).

## Groups on actions

Action visibility and execution are governed by the ACL engine (details in
[ACL](../guides/acl.md)):

**Who sees/opens** (`_is_action_visible`):

- `admin` → always;
- explicit groups on the action (`groups`) → the user must belong to at least
  one (manual override, takes precedence);
- otherwise, if the action is `admin`/`sys`: `model_group_access(read)` on
  the action's target model decides — identity models (`user`, `groups`,
  `group_users`, `model_groups_rule`, `model_fields_rule`) have no default
  ACL rows, so they stay admin-only "for free".

**Who can run it** (`_has_action_write_access`): the required operations
derive from the action (`save` → `create|update`, `copy` → `create`,
`delete` → `delete`) and must be granted by the model-level gate. A button
the user cannot run **does not appear**; direct execution gets `403`. One
exception: a `mode=form` action opens read-only (`editable=false`) instead of
denying access.

**Menus** (`menu_group`) are a separate gate (navigation folders without a
model target): `admin` → always; explicit groups on the menu_group; otherwise
admin+`technical_operator` heuristic for admin menus.

> Beware: record rules (`record_rules`) are the **union** of matching
> entries. An entry without `groups` (universal) grants also to whoever the
> per-group entries restrict: the default entry must be removed by hand when
> adding per-group rules.

## Example: a group of actions on a menu

The demo `menu_group` (the "Modulo Dati Persona" card) and its actions
(`data/action.json`): six actions on `modulo_dati_persona`, visible to the
`admin`/`user`/`operator`/`manager` groups. Card buttons come only from
actions with `component_type` in `form`/`resource`/`layout` (here `list_` and
`new_`); the others remain reachable inside the form.

## Next step

Actions can also **talk to the outside world**: service registry, companion
services and webhooks.
[Step 4 — External services](step-4-external-services.md).