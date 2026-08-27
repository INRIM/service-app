---
title: Step 2 — I componenti e le funzionalità
description: I componenti disponibili nei form service-app — campi Form.io, componenti custom Ozon, logica, select remote, file.
---

# I componenti e le funzionalità

<ol class="wizard-steps">
  <li class="wizard-done">Creare un form</li>
  <li class="wizard-current">I componenti</li>
  <li class="">Le action e i gruppi</li>
  <li class="">Servizi esterni</li>
  <li class="">Worker e Camunda</li>
</ol>

Lo schema dei form è Form.io standard: il frontend interpreta il contratto
del backend e adatta dinamicamente interfaccia, azioni e permessi — non c'è
una configurazione rigida per modello. Oltre ai componenti standard, il
backend e il frontend aggiungono funzionalità proprie.

## Componenti Form.io di base

- Layout: `columns`, `panel`, `well`, `tabs`, `fieldset`, `datagrid`,
  `container` — attraversati ricorsivamente dal frontend (valori di default
  inseriti senza sovrascrivere valori reali).
- Input: `textfield`, `textarea`, `select`, `number`, `checkbox`, `radio`,
  `datetime`, `file`, `button`, ...
- La **validazione Form.io** è eseguita prima delle azioni POST: gli errori
  impediscono l'invio e sono mostrati all'utente.
- La **logica** (`logic`) usa JSON Logic: un trigger (condizione) → una o più
  azioni (mostra/nascondi, abilita/disabilita, calcola un valore). Esempio
  reale dalla form "groups" della demo — il pulsante "Elimina" si nasconde se
  non si è admin:

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

## Select remote

Un `select` può prendere le opzioni da un **model interno** o da un **URL
remoto**, risolti server-side dal component. La config sta nelle `properties`
del componente:

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

Il frontend chiama `POST /get_remote_select` con `key` + `curr_model`: URL,
header e token vivono **sulla definizione del component**, mai nel payload
(contratto dettagliato in [Select remote](../guides/remote-select.md)).

## Componenti custom Ozon

| Componente | Cosa fa |
|---|---|
| `ozon_data_table` | lista Ozon incorporata dentro un form: esegue una action list indipendente, combina il contesto del record padre con la query (JSON Logic), può aprire/salvare record in modale e ricaricarsi dopo il salvataggio |
| JSON editor | basato su `vanilla-jsoneditor` — attivato con `properties.jeditor: "y"` su `textarea`/campi JSON |
| Editor WYSIWYG | basato su Quill, HTML sanificato (DOMPurify) |
| File/allegati | template dedicato agli allegati Ozon, download autenticato delegato al client API |
| `table` | tabella record dentro il form (azioni su una collection correlata) |
| `search_area` | area di ricerca/query configurata per model (query builder) |

Il mapping campo→tipo Python è fatto dal `ModelMaker` del backend leggendo il
`type` del campo: `textarea` → `str`, campo con `properties.type: "json"` →
`dict`, `select multiple` → `List[Any]`. I tipi generati devono combaciare
con quello che Mongo contiene davvero (per i dettagli vedi
[ACL](../guides/acl.md)).

## Cosa il form riceve dal backend

Ogni risposta action porta metadati che pilotano la UI:

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

- `mode` sceglie il renderer (`list`, `form`, `card`, `menu`, `layout`, ...).
- `editable AND can_create` decidono il readonly: se anche solo uno è `false`
  il viewer riceve `readOnly: true` e le azioni mutative spariscono.
- `fields.submit_action_name` / `fields.abandon_action_name` dicono al
  frontend quale action eseguire su Salva/Abbandona.
- `obfucated_fields` / `editable_fields` informano su quali campi l'utente
  vede in chiaro e può modificare.

## Liste e tabelle

- Le liste desktop usano **AG Grid**; su mobile le righe diventano card
  responsive.
- Caricamento JSON completo o stream **NDJSON**
  (`application/x-ndjson`) con contatori.
- Query builder con regole `AND`/`OR`, operatori coerenti col tipo campo e
  anteprima della query MongoDB generata.
- Ricerca veloce (`fields.fast_search`) e azioni rapide
  (`fields.fast_actions`) su selezione multipla.
- Import/export XLS/CSV/JSON per gli amministratori, con gestione
  dell'ownership (vedi [Import e ownership](../guides/import-ownership.md)).

## Prossimo step

I form da soli non fanno un'app: servono le **action** che li aprono, li
salvano e li mettono nel menu.
[Step 3 — Le action e i gruppi](step-3-actions.md).