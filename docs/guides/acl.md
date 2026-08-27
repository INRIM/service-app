---
title: ACL — model, record, field
description: Il motore ACL di service-app a 3 livelli — models_groups, record_rules, fields_rule — e dove viene applicato.
---

# ACL: model, record, field

Il motore ACL governa tre domini distinti che condividono la stessa fonte di
config (`component.properties`) con enforcement diverso:

| Livello | Config | Cosa decide | Fail mode |
|---|---|---|---|
| 1. Model | `models_groups` | CRUD+export sull'intero model, per gruppo | **fail-closed totale** (nessuna riga = nega tutto) |
| 2. Record | `models_restricted_fields.record_rules` | su quali **righe** si può agire | nessun match → **nega tutto** |
| 3. Field | `models_restricted_fields.fields_rule` | quali **campi** sono oscurati | oscura se nessun gruppo matcha |

## Attori e gruppi

- `groups` (collection): seed base `admin`, `user`, `operator`, `manager`,
  `dpo`, `technical_operator`, `gdpr`. Ogni riga ha `implied_groups`
  (gerarchia: `manager` implica `user`+`operator`) espansa a runtime, e
  opzionalmente `rule` (query mongo di appartenenza dinamica).
- `group_users` (collection): righe `(app_code, group, users[])` — fonte
  primaria di membership.
- A ogni request `apply_session_groups` ricalcola i gruppi della sessione:
  `group_users` + gruppi da `rule` + espansione `implied_groups`.
- **`is_admin` non viene da Keycloak**: sono admin gli uid presenti in
  `group_users` per il gruppo `admin`.

## Dove si configura: `component.properties`

Ogni component (model runtime) porta due chiavi JSON editabili da
form/builder: `models_groups` e `models_restricted_fields`. Il backend
inietta dei default sensati (`setdefault`) al salvataggio, così un model
nuovo parte con una baseline invece che aperto a tutti.

### `models_groups` (livello 1)

```json
{
  "rules": [
    {"groups": ["admin"], "actions": {"read": true, "create": true, "update": true, "delete": true, "export": true}},
    {"groups": ["user"],  "actions": {"read": true, "create": false, "update": false, "delete": false, "export": false}}
  ]
}
```

Regole di enforcement (`model_group_access`):

- admin → bypass, full access;
- non-admin: OR delle azioni concesse dalle righe dei propri gruppi;
- **fail-closed totale**: se nessuna riga copre un gruppo dell'attore — anche
  solo perché il model non ha righe — nega tutto.

Dove viene applicato: `load_record` (read/update), `list_records`/`stream_record`
(read negato → domain forzato a lista vuota, non errore), `upsert`
(create/update — nega con `403 {"message": "Model ACL denied"}`), visibilità
ed esecuzione delle action.

### `record_rules` (livello 2)

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

- I `filters` sono query mongo, con nodi json-logic risolti
  (`{"var": "user.uid"}`).
- Le azioni sono l'**unione (OR)** delle regole che matchano il record — un
  utente in più gruppi ottiene il più permissivo.
- **`filters: {}` matcha ogni record** — è la forma per "questo gruppo può
  sempre".
- **Fail-closed**: se il model ha `record_rules` e nessuna regola matcha, si
  nega tutto (a differenza del field masking, dove "nessun match" = baseline).
- `read` in lista: l'OR dei filtri delle regole con `read=true` restringe il
  dominio mongo (`record_rule_read_domain`).
- Su **update** la regola viene valutata sul record già persistito — così un
  record che la lista non aprirebbe non resta scrivibile con un POST diretto.
  Su **insert** il gate record-level non si applica (la creazione resta
  governata dal livello 1).

> **Attenzione alla entry universale.** Una entry senza `groups` (es. la
> default `filters: {"active": true}` con tutte le azioni) concede anche a chi
> le entry per gruppo restringono: va rimossa a mano quando si aggiungono
> regole per gruppo. Il sync logga un warning quando coesistono le due forme.

> **Bypass**: un admin puro **non** bypassa l'enforcement record-level sui
> model non-sys (coerentemente con `fields_rule`). L'unico bypass automatico
> è per i model `sys` — config applicativa condivisa (`action`, `menu_group`,
> `settings`, ...): la regola default `owner_uid == user.uid` nasconderebbe
> config condivisa a chiunque non l'abbia creata.

### `fields_rule` (livello 3)

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

- I gruppi in `allowed_groups` con `read: true` vedono i campi ristretti in
  chiaro; **tutti gli altri li vedono oscurati** (obfuscate → `null`).
- **Nessun bypass admin**: un campo GDPR-style non diventa visibile solo
  perché l'attore è admin.
- In scrittura (`enforce_write_acl`): i campi denied nel payload → audit su
  `field_acl_audit` + `403 {"message": "Field ACL denied"}`.
- Nota sulle chiavi: `resticted_fields` e `record_rules` (con le typo) sono
  il formato reale usato da builder/seed e codice — non refusi da correggere.

## Model-level × record-level: si combinano in AND

`models_groups` decide se il **verbo** è permesso al gruppo sul model;
`record_rules` può solo **restringere** l'insieme di righe per un verbo già
permesso — non concede mai un verbo negato a livello model. Se `user` ha solo
`read`, una record rule owner non gli permette comunque di creare.

## Esempio completo: workflow per stato

Caso: operator e manager creano ed editano; quando l'operator esegue
l'azione, `stato` passa `YYYY` → `XXXX`; da lì in poi **solo il manager** può
modificare.

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

Servono **due** entry per l'operator: la prima gli lascia la lettura di tutto
(altrimenti i record in `XXXX` non matcherebbero nulla e spariscono dalla
lista, fail-closed). L'entry `manager` ha `filters: {}` = ogni record.

A runtime: l'operator apre il record `YYYY` → `editable: true`; esegue la
transizione (la regola è valutata sul record **ancora in `YYYY`**) → il form
diventa readonly subito nella response del save; riaprendolo è readonly e un
POST diretto prende `403 Record ACL denied`.

**Cosa non copre**: il **valore** scritto — le record rule guardano lo stato
di partenza, mai il payload. Per vincolare la transizione, far scrivere il
campo al server o usare un'action dedicata.

## Action e menu (gate separati)

La visibilità delle action (`groups` esplicito, poi `model_group_access(read)`
sul model target per le action `admin`/`sys`) e l'euristica dei menu
`menu_group` (senza model target) sono descritte in
[Le action e i gruppi](../wizard/step-3-actions.md).

## Persistenza: `properties` è un campo atomico

Un save di component che ricostruisce `properties` da zero con solo alcune
chiavi cancellerebbe silenziosamente `models_groups`/`models_restricted_fields`
(`$set` tratta `properties` come un blocco, senza merge chiave-per-chiave).
Il backend ripristina le chiavi ACL dal component esistente quando il payload
non le porta.

## Model identity

`{"user", "groups", "group_users", "model_groups_rule", "model_fields_rule"}`
sono esclusi dai default ACL: le tabelle del motore ACL stesso restano
admin-only per costruzione — un non-admin non può leggere le regole ACL di
altri model.