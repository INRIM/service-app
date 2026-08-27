---
title: Example modifications
description: Three modifications to try on the service-app demo — add a field, create a new plugin, configure an ACL rule.
---

# Example modifications

Three progressive examples to try on the demo (`inrim-forms-demo`), to make
your first experiments with the concepts of the
[guided path](../wizard/step-1-create-form.md).

## Example 1 — Add a field to the existing form

The demo plugin form is "Modulo Dati Persona" (`demo/plugin/schema/
components.json`), organized in `panel` and `columns`:

- `datiPersonali` (panel) → `cognome`, `nome`, `dataDiNascita`, `dateStart`,
  `dateEnd`, `contatti` (datagrid: `indirizzo`, `email`, `phoneNumber`).

Goal: add a `codiceFiscale` field.

1. Edit `demo/plugin/schema/components.json` and insert the field inside the
   `datiPersonali` panel (same level as the existing `columns`):

   ```json
   {
     "label": "Codice Fiscale",
     "tableView": true,
     "key": "codiceFiscale",
     "type": "textfield",
     "input": true,
     "validate": { "pattern": "^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$", "patternMessage": "Codice fiscale non valido" }
   }
   ```

   (the pattern above is the format regex, not a real code).

2. Restart the backend — plugins are upserted at every startup:

   ```bash
   demo/run_demo.sh down && demo/run_demo.sh up
   ```

3. Open `http://localhost:4200`, fill in the form and save.
4. Verify in Mongo:

   ```bash
   docker exec ozon-env-app-db mongosh -u admin -p "$MONGO_PASS" \
     --eval 'db.modulo_dati_persona.find({}, {codiceFiscale: 1}).limit(3)'
   ```

Note: every component field generates the matching field in the runtime model
(`ModelMaker`). If the field does not appear, check the startup error
(`docker logs ozon-env-app`) — that is the mechanism that surfaces, for
example, the known `phoneNumber` unsupported-type issue.

## Example 2 — Create a new plugin (new form with card)

Goal: your own "Richiesta Ferie" (leave request) form, as a separate plugin.

1. Create the structure (copy the demo plugin pattern):

   ```
   demo/plugin-ferie/
   ├── config.json
   ├── schema/components.json
   └── data/
       ├── menu_group.json
       └── action.json
   ```

2. `config.json`:

   ```json
   {
     "module_name": "richiesta_ferie",
     "schema": "/schema/components.json",
     "datas": [
       { "menu_group": "/data/menu_group.json" },
       { "action": "/data/action.json" }
     ],
     "depends": []
   }
   ```

3. `schema/components.json` — the form (careful: `app_code` must be the
   **empty string**, not a list — Pydantic validation rejects a list):

   ```json
   [
     {
       "rec_name": "richiesta_ferie",
       "title": "Richiesta Ferie",
       "type": "resource",
       "display": "form",
       "app_code": "",
       "authenticate": true,
       "sys": false,
       "demo": false,
       "components": [
         { "label": "Dipendente", "key": "dipendente", "type": "textfield", "input": true },
         { "label": "Dal", "key": "dal", "type": "datetime", "input": true },
         { "label": "Al", "key": "al", "type": "datetime", "input": true },
         { "label": "Note", "key": "note", "type": "textarea", "input": true },
         { "type": "button", "label": "Submit", "key": "submit", "disableOnInvalid": true, "input": true }
       ],
       "properties": { "rheader": "1", "rfooter": "1" }
     }
   ]
   ```

4. `data/menu_group.json` and `data/action.json` — start from the demo plugin
   seeds (`demo/plugin/data/`) and replace `modulo_dati_persona` with
   `richiesta_ferie`; `apps: ["demo"]`, `parent: ""` and `admin: false` stay.
   Remember the details that make the card appear/disappear:

   - the card shows only if at least one **non-`sys`** action points to the
     `menu_group`;
   - buttons come only from actions with `component_type` in
     `form`/`resource`/`layout` (`list_` and `new_`);
   - configure `groups` to make it visible to the right groups.

5. Mount the plugin: add the bind mount in `docker-compose.demo.yml` (next to
   `/plugins/demo`) and restart with `demo/run_demo.sh up`.
6. The "Richiesta Ferie" card appears in the dashboard; list, form and saving
   work via `list_richiesta_ferie`, `new_richiesta_ferie`,
   `form_form_richiesta_ferie`, `submit_richiesta_ferie`.

Alternative without seeds: create the form from the **builder** enabling
`create_menu_dashboard` — it generates the same actions (`list_`, `new_`,
`form_form_`, `submit_`, `copy_`, `delete_`) and the card.

## Example 3 — Configure an ACL rule (state-based workflow)

Goal: on `richiesta_ferie`, the `operator` can edit only requests
**pending**; once approved (`stato` field → `approvata`), only the `manager`
can still act. Use the demo users (`operator/operator`, `manager/manager`).

1. As `admin`, open the `richiesta_ferie` form with the builder and configure
   in `properties.models_groups` (layer 1 — who touches the model):

   ```json
   {"rules": [{"groups": ["operator", "manager"],
               "actions": {"read": true, "create": true, "update": true,
                           "delete": false, "export": true}}]}
   ```

2. In `properties.models_restricted_fields.record_rules` (layer 2 — which
   rows), **remove the universal default entry** (the one without `groups`:
   it stays in the union and would grant update on approved records too) and
   add:

   ```json
   {"record_rules": [
     {"groups": ["operator"], "filters": {"active": true}, "actions": {"read": true}},
     {"groups": ["operator"], "filters": {"stato": "in_attesa"}, "actions": {"read": true, "update": true}},
     {"groups": ["manager"],  "filters": {}, "actions": {"read": true, "update": true, "delete": true}}
   ]}
   ```

   Two entries are needed for the operator: the first keeps read access to
   everything (otherwise approved records vanish from the list —
   fail-closed).

3. Try with the two users:

   - `operator`: opens a request with `stato: in_attesa` → `editable: true`;
     saves it approved (`stato` → `approvata`) → the form becomes read-only
     **in the same response**;
   - `operator`: reopens the approved record → read-only; a direct POST gets
     `403 Record ACL denied`;
   - `manager`: `filters: {}` always matches → edits any record.

4. Verify field masking (layer 3): add a sensitive field to
   `fields_rule.resticted_fields` and grant read to a single group — everyone
   else sees it `null` in list and form, **including the admin** (field
   masking has no admin bypass).

What the rule does **not** cover: the written value — the operator, on a
record in `in_attesa`, can write any `stato` value. To constrain the
transition, have the server write the field or use a dedicated action.