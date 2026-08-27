---
title: Step 3 — Le action e i gruppi
description: Action router, menu, dashboard, action di default e gruppi ACL — come il backend pilota navigazione e permessi.
---

# Le action e i gruppi

<ol class="wizard-steps">
  <li class="wizard-done">Creare un form</li>
  <li class="wizard-done">I componenti</li>
  <li class="wizard-current">Le action e i gruppi</li>
  <li class="">Servizi esterni</li>
  <li class="">Worker e Camunda</li>
</ol>

Tutto ciò che l'utente vede e fa passa dall'**action router** (`/action/...`).
Un'**action** è un record nella collection `action`: il client non hardcoda
logiche per endpoint specifici — legge i metadati dell'action e reagisce.

## L'action come record

Campi rilevanti:

| Campo | Significato |
|---|---|
| `rec_name` | identificativo action (diventa `{name}` in `/action/{name}`) |
| `model` | model business target — determina su quale collezione si legge/scrive |
| `view_name` | override opzionale dello **schema UI** (non del model dati) |
| `mode` | output atteso (`list`, `form`, ...) |
| `action_type` | semantica: `menu`, `window`, `process_task`, `save`, `copy`, `delete` |
| `component_type` | per action su component: `form`, `resource`, `layout` |
| `list_query` | filtro base per le action di lista |
| `groups` | gruppi ACL che possono vedere/aprire l'action |
| `title`, `button_icon` | rendering |
| `url_action` | rotta da invocare (canonica per i pulsanti di menu) |
| `builder_enabled` | flag per la UI builder |

Il `model` è il centro del comportamento: determina la collezione, il dominio
effettivo (`get_domain`) e il conteggio `number` delle card. Lo schema UI
viene da `view_name` se valorizzato, altrimenti da `model` — così
`list_doc_beni_servizi` può leggere da `model=documento` ma usare lo schema
`documento_beni_servizi`.

## Le 6 action di default

Quando crei un form (builder o plugin), il backend genera:

| Action | mode | action_type | A cosa serve |
|---|---|---|---|
| `list_<model>` | list | window | lista/tabella |
| `new_<model>` | form | menu | nuovo record (via `next_action`) |
| `form_form_<model>` | form | window | form di dettaglio (create/edit) |
| `submit_<model>` | — | save | salvataggio (submit della form) |
| `copy_<model>` | — | copy | duplica record |
| `delete_<model>` | — | delete | soft delete |

Il naming può cambiare per progetto: il client deve basarsi su
`fields.submit_action_name`, `fields.abandon_action_name` e `mode`, non sul
nome.

## Endpoint dell'action router

```text
GET  /action/menu[/{parent}]        menu raggruppato per menu_group
GET  /action/dashboard[/{parent}]   card della dashboard (mode=card)
GET  /action/layout[/{name}]        bootstrap della UI (schema+menu+settings)
GET  /action/next_action/{curr}[/{rec_name}]   passo successivo (redirect)
GET|POST|DELETE /action/{name}[/{rec_name}]   esecuzione action
```

Tutte le risposte condividono l'`envelope` `ResponseObject`: il client fa
switch su `content.mode`, mai sul path chiamato. Contratto completo in
[Riferimento action router](../reference/action-router.md).

Flusso tipico del client:

1. `GET /action/layout` → schema, menu, branding (`settings`).
2. `GET /action/dashboard` → card (ogni bottone porta `number` = conteggio
   record della lista, calcolato dal backend con `list_query` + ACL).
3. Click su una action → `GET /action/{name}` → render per `mode`.
4. Save → `POST /action/{name}[/{rec_name}]` (o `submit_action_name`).
5. Delete → `DELETE /action/{name}/{rec_name}` (soft delete).

## I gruppi sulle action

La visibilità e l'esecuzione delle action sono governate dal motore ACL
(dettagli in [ACL](../guides/acl.md)):

**Chi vede/apre** (`_is_action_visible`):

- `admin` → sempre;
- gruppi espliciti sull'action (`groups`) → l'utente deve appartenere ad
  almeno uno (override manuale, precede tutto);
- altrimenti, se l'action è `admin`/`sys`: decide `model_group_access(read)`
  sul model target — i model identity (`user`, `groups`, `group_users`,
  `model_groups_rule`, `model_fields_rule`) non hanno righe ACL di default,
  quindi restano admin-only "gratis".

**Chi la esegue** (`_has_action_write_access`): le operazioni richieste
derivano dall'action (`save` → `create|update`, `copy` → `create`,
`delete` → `delete`) e devono essere concesse dal gate model-level. Un
pulsante che l'utente non può eseguire **non compare**; l'esecuzione diretta
prende `403`. Unica eccezione: una action `mode=form` si apre in sola lettura
(`editable=false`) invece di negare l'accesso.

**I menu** (`menu_group`) sono un gate a parte (cartelle di navigazione senza
model target): `admin` → sempre; gruppi espliciti sul menu_group; altrimenti
euristica admin+`technical_operator` per i menu admin.

> Attenzione: le regole di record (`record_rules`) sono l'**unione** delle
> entry che matchano. Una entry senza `groups` (universale) concede anche a
> chi le entry per gruppo restringono: la entry di default va rimossa a mano
> quando si aggiungono regole per gruppo.

## Esempio: gruppo di azioni su un menu

Il `menu_group` della demo (card "Modulo Dati Persona") e le sue action
(`data/action.json`): sei action su `modulo_dati_persona`, visibili ai
gruppi `admin`/`user`/`operator`/`manager`. I bottoni della card arrivano
solo dalle action con `component_type` in `form`/`resource`/`layout`
(qui `list_` e `new_`); le altre restano raggiungibili dentro la form.

## Prossimo step

Le action possono anche **parlare con il mondo esterno**: service registry,
companion service e webhooks.
[Step 4 — I servizi esterni](step-4-external-services.md).