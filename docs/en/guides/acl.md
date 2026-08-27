---
title: ACL — model, record, field
description: The service-app 3-layer ACL engine — models_groups, record_rules, fields_rule — and where it is enforced.
---

# ACL: model, record, field

The ACL engine governs three distinct domains that share the same config
source (`component.properties`) with different enforcement:

| Layer | Config | Decides | Fail mode |
|---|---|---|---|
| 1. Model | `models_groups` | CRUD+export on the whole model, per group | **totally fail-closed** (no rows = deny all) |
| 2. Record | `models_restricted_fields.record_rules` | which **rows** can be acted on | no match → **deny all** |
| 3. Field | `models_restricted_fields.fields_rule` | which **fields** are masked | masks when no group matches |

## Actors and groups

- `groups` (collection): base seed `admin`, `user`, `operator`, `manager`,
  `dpo`, `technical_operator`, `gdpr`. Each row carries `implied_groups`
  (hierarchy: `manager` implies `user`+`operator`) expanded at runtime, and
  optionally `rule` (a mongo query for dynamic membership).
- `group_users` (collection): `(app_code, group, users[])` rows — the primary
  membership source.
- On every request `apply_session_groups` recomputes the session groups:
  `group_users` + groups from `rule` + `implied_groups` expansion.
- **`is_admin` does not come from Keycloak**: admins are the uids present in
  `group_users` for the `admin` group.

## Where it is configured: `component.properties`

Every component (runtime model) carries two JSON keys editable from
form/builder: `models_groups` and `models_restricted_fields`. The backend
injects sensible defaults (`setdefault`) on save, so a new model starts with a
baseline instead of being open to everyone.

### `models_groups` (layer 1)

```json
{
  "rules": [
    {"groups": ["admin"], "actions": {"read": true, "create": true, "update": true, "delete": true, "export": true}},
    {"groups": ["user"],  "actions": {"read": true, "create": false, "update": false, "delete": false, "export": false}}
  ]
}
```

Enforcement rules (`model_group_access`):

- admin → bypass, full access;
- non-admin: OR of the actions granted by the rows of their groups;
- **totally fail-closed**: if no row covers one of the actor's groups — even
  just because the model has no rows — everything is denied.

Where it applies: `load_record` (read/update), `list_records`/`stream_record`
(read denied → domain forced to an empty list, not an error), `upsert`
(create/update — denied with `403 {"message": "Model ACL denied"}`), action
visibility and execution.

### `record_rules` (layer 2)

```json
{
  "record_rules": [
    {
      "groups": ["operator"],
      "filters": {"stato": "YYYY"},
      "actions": {"read": true, "update": true}
    },
    {
      "groups": ["manager"],
      "filters": {},
      "actions": {"read": true, "update": true, "delete": true}
    }
  ]
}
```

- `filters` are mongo queries, with json-logic nodes resolved
  (`{"var": "user.uid"}`).
- Actions are the **union (OR)** of all matching rules — a user in several
  groups gets the most permissive one.
- **`filters: {}` matches every record** — the form for "this group can
  always".
- **Fail-closed**: if the model has `record_rules` and no rule matches,
  everything is denied (unlike field masking, where "no match" = baseline).
- `read` on lists: the OR of the filters of rules with `read=true` restricts
  the mongo domain (`record_rule_read_domain`).
- On **update** the rule is evaluated against the already-persisted record —
  so a record the list would not open cannot stay writable via a direct POST.
  On **insert** the record-level gate does not apply (creation stays governed
  by layer 1).

> **Beware of the universal entry.** An entry without `groups` (e.g. the
> default `filters: {"active": true}` with all actions) grants also to
> whoever the per-group entries restrict: remove it by hand when adding
> per-group rules. The sync logs a warning when both forms coexist.

> **Bypass**: a pure admin **does not** bypass record-level enforcement on
> non-sys models (consistent with `fields_rule`). The only automatic bypass is
> for `sys` models — shared application config (`action`, `menu_group`,
> `settings`, ...): the default `owner_uid == user.uid` rule would hide shared
> config from anyone who didn't create it.

### `fields_rule` (layer 3)

```json
{
  "fields_rule": {
    "resticted_fields": ["codicefiscale", "iban"],
    "allowed_groups": [
      {"groups": ["gdpr"], "actions": {"read": true}},
      {"groups": ["dpo"],  "actions": {"read": true}}
    ]
  }
}
```

- Groups in `allowed_groups` with `read: true` see the restricted fields in
  clear; **everyone else sees them masked** (obfuscate → `null`).
- **No admin bypass**: a GDPR-style field does not become visible just
  because the actor is admin.
- On write (`enforce_write_acl`): denied fields in the payload → audit into
  `field_acl_audit` + `403 {"message": "Field ACL denied"}`.
- Key naming note: `resticted_fields` and `record_rules` (with the typos) are
  the real format used by builder/seeds and code — not typos to fix.

## Model-level × record-level: combined in AND

`models_groups` decides whether the **verb** is granted to the group on the
model; `record_rules` can only **restrict** the set of rows for an already
granted verb — it never grants a verb denied at model level. If `user` only
has `read`, an owner record rule still does not let them create.

## Full example: state-based workflow

Case: operator and manager both create and edit; when the operator runs the
action, `stato` goes `YYYY` → `XXXX`; from then on **only the manager** can
edit.

```json
// Layer 1 — models_groups
{"rules": [{"groups": ["operator", "manager"],
            "actions": {"read": true, "create": true, "update": true,
                        "delete": false, "export": true}}]}

// Layer 2 — record_rules
{"record_rules": [
  {"groups": ["operator"], "filters": {"active": true}, "actions": {"read": true}},
  {"groups": ["operator"], "filters": {"stato": "YYYY"}, "actions": {"read": true, "update": true}},
  {"groups": ["manager"],  "filters": {}, "actions": {"read": true, "update": true, "delete": true}}
]}
```

Two entries are needed for the operator: the first keeps read access to
everything (otherwise records in `XXXX` would match nothing and vanish from
the list — fail-closed). The `manager` entry has `filters: {}` = every
record.

At runtime: the operator opens the `YYYY` record → `editable: true`; performs
the transition (the rule is evaluated against the record **still in `YYYY`**)
→ the form becomes read-only right in the save response; reopening it is
read-only and a direct POST gets `403 Record ACL denied`.

**What it does not cover**: the written **value** — record rules look at the
starting state, never at the payload. To constrain the transition, have the
server write the field or use a dedicated action.

## Actions and menus (separate gates)

Action visibility (explicit `groups`, then `model_group_access(read)` on the
target model for `admin`/`sys` actions) and the `menu_group` heuristic
(no model target) are described in
[Actions and groups](../wizard/step-3-actions.md).

## Persistence: `properties` is an atomic field

A component save that rebuilds `properties` from scratch with only a few keys
would silently wipe `models_groups`/`models_restricted_fields` (`$set` treats
`properties` as one block, without key-by-key merge). The backend restores
the ACL keys from the existing component when the payload does not carry
them.

## Identity models

`{"user", "groups", "group_users", "model_groups_rule", "model_fields_rule"}`
are excluded from default ACLs: the ACL engine's own tables stay admin-only
by construction — a non-admin cannot read other models' ACL rules.