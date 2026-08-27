---
title: Query field ACL gate
description: Validazione server-side di query e order nelle liste — operatori allowlist e cross-check con l'ACL di campo.
---

# Query field ACL gate

Validazione server-side su `query` (filtro find-style Mongo) e `order`
(ordinamento) applicata a **ogni lettura in modalità lista**:

- `POST /list/{model}`
- `GET|POST /action/{name}` quando l'action ha `mode = list`
- `POST /filter/fast_search/{action_name}`

Tutti e tre finiscono nello stesso metodo backend
(`Service.list_records` / `Service.stream_record`), quindi la regola è
identica per tutti.

## Perché esiste

L'ACL di campo maschera i campi denied/obfuscate **solo nel payload di
risposta**. Senza questo gate, un client potrebbe mettere lo stesso campo
nella `query` o nell'`order` e dedurne il valore reale da quali righe tornano,
dal loro conteggio o dal loro rank:

```
GET /action/list_dipendenti?order=salary:desc&limit=1
```

rivela chi guadagna di più senza che `salary` compaia mai in una risposta. Il
gate chiude questo canale validando `query`/`order` **prima di qualunque
lettura sul database**.

## 1. Allowlist operatori

`query` può usare solo questi operatori:

```text
$eq $ne $in $nin $gt $gte $lt $lte
$and $or $nor $not
$exists $all $size $elemMatch $regex $options
```

Qualunque altro operatore viene rifiutato — in particolare `$where`, `$expr`,
`$function`, `$accumulator`, `$text`, `$mod`, `$type`, `$jsonSchema` e gli
operatori geo. Non esiste un modo supportato per usarli dal client: ricostrui
la condizione con gli operatori consentiti, oppure spostala server-side
(`list_query` su action/component).

```json
// Rifiutata (403)
{"message": "Query operator not allowed", "operator": "$where"}
```

## 2. Cross-check con l'ACL di campo

Anche usando solo operatori consentiti, se `query` o `order` referenziano un
field path denied/obfuscated per la sessione corrente su quel model, la
richiesta viene rifiutata — quel campo non è utilizzabile per filtrare o
ordinare, non solo nascosto in risposta.

```json
{"message": "Query references ACL-denied fields", "fields": ["salary"]}
{"message": "Order references ACL-denied fields", "fields": ["salary"]}
```

Status HTTP: `403` in tutti i casi.

## Esempi

Consentita:

```json
{
  "query": {"status": {"$in": ["open", "pending"]}, "name": {"$regex": "^A"}},
  "order": "created_at:desc"
}
```

Rifiutata (operatore non consentito):

```json
{"query": {"$where": "this.status == 'open'"}}
```

Rifiutata (campo ACL-denied, assumendo `salary` mascherato per la sessione):

```json
{"query": {"salary": {"$gt": 50000}}}
{"order": "salary:desc"}
```

## Indicazioni per il client

- **Non offrire controlli di filtro/ordinamento su campi che l'utente non può
  leggere.** Pilota i campi filtrabili/ordinabili con gli stessi metadati ACL
  usati per nascondere il campo (o con `obfucated_fields` della risposta).
- **Tratta il `403` come caso distinto** da un errore di auth generico:
  mostralo come "questo campo non è utilizzabile per filtrare/ordinare", non
  come schermata bloccante — è un esito atteso con un query builder
  dinamico.
- **I path annidati funzionano come dotted path Mongo** (`address.city`);
  `$and`/`$or`/`$nor` si compongono come al solito; `$elemMatch` è consentito
  per gli array di subdocumenti.
- **Nessun workaround client-side per `$where`/`$expr`.** Se serve una
  condizione calcolata, calcola lato client prima di inviare, oppure chiedi
  al backend di aggiungerla come `list_query` fisso.