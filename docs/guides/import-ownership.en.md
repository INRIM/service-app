---
title: Import and ownership
description: POST /import/{model}, take_ownership and the record ownership rules during import.
---

# Import and ownership

Reference: `POST /import/{model}`.

## `take_ownership`

Import accepts a parameter **in the query string**:

```
POST /import/{model}?take_ownership=false        # default
POST /import/{model}?take_ownership=true
```

| Value | Effect on a NEW record |
|---|---|
| `false` (default) | if the payload carries `owner_uid`, that value is written: the record stays owned by the original owner |
| `true` | the `owner_*` fields are overwritten with the importing user |

No other endpoint changes behavior: on ordinary writes, the writer is the
owner.

## Why the gate exists

`owner_uid` is not a descriptive field: it is an **authorization input**.

- `record_rules` filter records on `owner_uid == user.uid`;
- field rules support ownership-conditioned reveal/write.

Creating a record owned by another user means assigning them visibility and
write permissions: it is an admin operation, and the gate is server-side.

## The rules

1. **The parameter goes in the query string, never in the body.** The body is
   the record and has no allowlist: a `take_ownership` in the payload would
   become a record field.

   ```js
   // YES
   await fetch(`/import/${model}?take_ownership=true`, {
       method: "POST",
       headers: {"Content-Type": "application/json", ...authHeaders},
       body: JSON.stringify(record),
   });

   // NO — it ends up in the record
   body: JSON.stringify({...record, take_ownership: true})
   ```

2. **Do not send `owner_uid` on ordinary writes.** On
   `POST /{model}/{rec_name}` it is ignored on update and overwritten with
   the session on insert. Applies to the "duplicate"/"save as new" flows.

3. **The 403 with `foreign_owner_requires_admin`.** With
   `take_ownership=false`, if the payload carries an `owner_uid` different
   from the current user and the user is not admin:

   ```json
   {
     "detail": {
       "message": "Importing a record owned by another user requires admin; pass take_ownership=true to import it under your own uid",
       "reason": "foreign_owner_requires_admin",
       "model": "component"
     }
   }
   ```

   The right UI action: re-propose the import with `take_ownership=true`,
   explaining the records will be owned by the current user. Discriminate on
   the `reason`, not on the message text. The `403` **does not** trigger if
   the payload has no `owner_uid`, if the owner is already the current user,
   or if `take_ownership=true` is passed.

4. **The 403 with `owner_uid_denied_by_field_acl`.** If a
   `field_acl_policy` denies `owner_uid` on `create`, the field is stripped
   from the payload before the gate and the import with
   `take_ownership=false` fails. No silent fallback: the owner becomes the
   importer only with `take_ownership=true` or with a payload without
   `owner_uid`.

5. **The other `owner_*` fields are not decided by the payload.** With
   `take_ownership=false` only `owner_uid` survives: `owner_name`,
   `owner_mail`, `owner_sector`, ... are re-read from the local `user`
   collection by `uid`. If the uid does not exist locally, the import does
   not fail — the record enters with the original `owner_uid` and empty
   `owner_*` fields.

6. **`id`/`_id` in the payload are stripped**: they are the identity of the
   source instance. Import matching stays on `rec_name` — re-importing the
   same file updates the same record.

7. **Ownership of an existing record can never be reassigned**: if the
   `rec_name` already exists, the import is an update and the payload
   `owner_*` fields are stripped, always, for everyone.

## Suggested UI

In the import dialog, a single choice:

- **Keep the original owners** → `take_ownership=false` — admins only
  (`session.is_admin` is already available from `GET /get_session`);
- **Import under my name** → `take_ownership=true` — always available.

Default: "keep" for admins, "under my name" for everyone else — that way the
403 becomes an edge case, not the normal flow.