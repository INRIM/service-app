---
title: Query field ACL gate
description: Server-side validation of list query and order — operator allowlist and cross-check with the field ACL.
---

# Query field ACL gate

Server-side validation of `query` (find-style Mongo filter) and `order`
(sorting) applied to **every list-mode read**:

- `POST /list/{model}`
- `GET|POST /action/{name}` when the action has `mode = list`
- `POST /filter/fast_search/{action_name}`

All three end up in the same backend method
(`Service.list_records` / `Service.stream_record`), so the rule is identical
for all of them.

## Why it exists

Field-level ACL masks denied/obfuscated fields **only in the response
payload**. Without this gate, a client could put the same field in the
`query` or `order` and infer its real value from which rows come back, from
their count, or from their rank:

```
GET /action/list_dipendenti?order=salary:desc&limit=1
```

reveals who earns the most without `salary` ever appearing in a response. The
gate closes this channel by validating `query`/`order` **before any database
read**.

## 1. Operator allowlist

`query` can only use these operators:

```text
$eq $ne $in $nin $gt $gte $lt $lte
$and $or $nor $not
$exists $all $size $elemMatch $regex $options
```

Any other operator is rejected — in particular `$where`, `$expr`,
`$function`, `$accumulator`, `$text`, `$mod`, `$type`, `$jsonSchema` and the
geo operators. There is no supported way to use them from the client:
rebuild the condition with the allowed operators, or move it server-side
(`list_query` on action/component).

```json
// Rejected (403)
{"message": "Query operator not allowed", "operator": "$where"}
```

## 2. Cross-check with the field ACL

Even using only allowed operators, if `query` or `order` reference a
field path denied/obfuscated for the current session on that model, the
request is rejected — that field cannot be used to filter or sort, not just
hidden in the response.

```json
{"message": "Query references ACL-denied fields", "fields": ["salary"]}
{"message": "Order references ACL-denied fields", "fields": ["salary"]}
```

HTTP status: `403` in all cases.

## Examples

Allowed:

```json
{
  "query": {"status": {"$in": ["open", "pending"]}, "name": {"$regex": "^A"}},
  "order": "created_at:desc"
}
```

Rejected (operator not allowed):

```json
{"query": {"$where": "this.status == 'open'"}}
```

Rejected (ACL-denied field, assuming `salary` masked for the session):

```json
{"query": {"salary": {"$gt": 50000}}}
{"order": "salary:desc"}
```

## Client guidance

- **Do not offer filter/sort controls on fields the user cannot read.** Drive
  the filterable/sortable fields with the same ACL metadata used to hide the
  field (or with the response's `obfucated_fields`).
- **Treat the `403` as a distinct case** from a generic auth error: show it
  as "this field cannot be used for filtering/sorting", not as a blocking
  error screen — it is an expected outcome with a dynamic query builder.
- **Nested paths work as normal Mongo dotted paths** (`address.city`);
  `$and`/`$or`/`$nor` compose as usual; `$elemMatch` is allowed for arrays of
  subdocuments.
- **No client-side workaround for `$where`/`$expr`.** If you need a computed
  condition, compute it client-side before sending, or ask the backend to add
  it as a fixed `list_query`.