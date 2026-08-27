---
title: Modifiche di esempio
description: Tre modifiche da provare sulla demo service-app — aggiungere un campo, creare un plugin nuovo, configurare una regola ACL.
---

# Modifiche di esempio

Tre esempi progressivi da provare sulla demo (`inrim-forms-demo`), per fare
le prime prove con i concetti del [percorso guidato](../wizard/step-1-create-form.md).

## Esempio 1 — Aggiungere un campo alla form esistente

La form del plugin demo è "Modulo Dati Persona" (`demo/plugin/schema/
components.json`), organizzata in `panel` e `columns`:

- `datiPersonali` (panel) → `cognome`, `nome`, `dataDiNascita`, `dateStart`,
  `dateEnd`, `contatti` (datagrid: `indirizzo`, `email`, `phoneNumber`).

Obiettivo: aggiungere il campo `codiceFiscale`.

1. Modifica `demo/plugin/schema/components.json` e inserisci il campo dentro
   il panel `datiPersonali` (stesso livello dei `columns` esistenti):

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

   (il pattern qui sopra è la regex del formato, non un codice reale).

2. Riavvia il backend — i plugin vengono upsertati a ogni avvio:

   ```bash
   demo/run_demo.sh down && demo/run_demo.sh up
   ```

3. Apri `http://localhost:4200`, compila la form e salva.
4. Verifica in Mongo:

   ```bash
   docker exec ozon-env-app-db mongosh -u admin -p "$MONGO_PASS" \
     --eval 'db.modulo_dati_persona.find({}, {codiceFiscale: 1}).limit(3)'
   ```

Nota: ogni campo del component genera il campo corrispondente nel model
runtime (`ModelMaker`). Se il campo non compare, controlla l'errore di
avvio (`docker logs ozon-env-app`) — è il meccanismo che rende visibile, per
esempio, il problema noto del tipo `phoneNumber` non supportato.

## Esempio 2 — Creare un plugin nuovo (nuova form con card)

Obiettivo: una form "Richiesta Ferie" propria, come plugin separato.

1. Crea la struttura (copia il pattern del plugin demo):

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

3. `schema/components.json` — la form (fai attenzione: `app_code` deve essere
   la **stringa vuota**, non una lista — la validazione Pydantic la respinge):

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

4. `data/menu_group.json` e `data/action.json` — parti dalle seed del plugin
   demo (`demo/plugin/data/`) e sostituisci `modulo_dati_persona` con
   `richiesta_ferie`, `apps: ["demo"]` resta, `parent: ""` e `admin: false`
   restano. Ricorda i dettagli che fanno comparire/sparire la card:

   - la card compare solo se almeno una action **non `sys`** punta al
     `menu_group`;
   - i bottoni arrivano solo dalle action con `component_type` in
     `form`/`resource`/`layout` (`list_` e `new_`);
   - configura `groups` per renderla visibile ai gruppi giusti.

5. Monta il plugin: aggiungi il bind mount in `docker-compose.demo.yml`
   (accanto a `/plugins/demo`) e riavvia con `demo/run_demo.sh up`.
6. La card "Richiesta Ferie" appare in dashboard; la lista, la form e il
   salvataggio funzionano via `list_richiesta_ferie`, `new_richiesta_ferie`,
   `form_form_richiesta_ferie`, `submit_richiesta_ferie`.

Alternativa senza seed: crea la form dal **builder** attivando
`create_menu_dashboard` — genera le stesse action (`list_`, `new_`,
`form_form_`, `submit_`, `copy_`, `delete_`) e la card.

## Esempio 3 — Configurare una regola ACL (workflow per stato)

Obiettivo: su `richiesta_ferie`, l'`operator` può modificare solo le
richieste **in attesa**; approvata (campo `stato` → `approvata`), solo il
`manager` può ancora agire. Usa gli utenti demo
(`operator/operator`, `manager/manager`).

1. Da `admin`, apri la form `richiesta_ferie` col builder e configura in
   `properties.models_groups` (livello 1 — chi tocca il model):

   ```json
   {"rules": [{"groups": ["operator", "manager"],
               "actions": {"read": true, "create": true, "update": true,
                           "delete": false, "export": true}}]}
   ```

2. In `properties.models_restricted_fields.record_rules` (livello 2 — su
   quali righe), **rimuovi la entry universale di default** (quella senza
   `groups`: resta in unione e concederebbe update anche sui record
   approvati) e aggiungi:

   ```json
   {"record_rules": [
     {"groups": ["operator"], "filters": {"active": true}, "actions": {"read": true}},
     {"groups": ["operator"], "filters": {"stato": "in_attesa"}, "actions": {"read": true, "update": true}},
     {"groups": ["manager"],  "filters": {}, "actions": {"read": true, "update": true, "delete": true}}
   ]}
   ```

   Servono due entry per l'operator: la prima gli lascia la lettura di tutto
   (altrimenti i record approvati spariscono dalla lista — fail-closed).

3. Prova con i due utenti:

   - `operator`: apre una richiesta con `stato: in_attesa` → `editable: true`;
     la salva approvata (campo `stato` → `approvata`) → il form diventa
     readonly **nella stessa response**;
   - `operator`: riapre il record approvato → readonly; un POST diretto
     prende `403 Record ACL denied`;
   - `manager`: `filters: {}` matcha sempre → edita qualunque record.

4. Verifica il field masking (livello 3): aggiungi un campo sensibile in
   `fields_rule.resticted_fields` e concedi la lettura solo a un gruppo —
   gli altri lo vedono `null` in lista e form, **incluso l'admin** (il field
   masking non ha bypass admin).

Cosa la regola **non** copre: il valore scritto — l'operator sul record in
`in_attesa` può scrivere `stato` con qualunque valore. Per vincolare la
transizione, far scrivere il campo al server o usare un'action dedicata.