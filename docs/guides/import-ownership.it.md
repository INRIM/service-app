---
title: Import e ownership
description: POST /import/{model}, take_ownership e le regole di ownership dei record nell'importazione.
---

# Import e ownership

Riferimento: `POST /import/{model}`.

## `take_ownership`

L'import accetta un parametro **in query string**:

```
POST /import/{model}?take_ownership=false        # default
POST /import/{model}?take_ownership=true
```

| Valore | Effetto su un record NUOVO |
|---|---|
| `false` (default) | se il payload contiene `owner_uid`, quel valore viene scritto: il record resta intestato all'owner originale |
| `true` | gli `owner_*` vengono sovrascritti con l'utente che sta importando |

Nessun altro endpoint cambia comportamento: sulle scritture normali chi
scrive è l'owner.

## Perché il gate esiste

`owner_uid` non è un campo descrittivo: è un **input dell'autorizzazione**.

- le `record_rules` filtrano i record su `owner_uid == user.uid`;
- le regole di campo supportano il reveal/write condizionato all'ownership.

Creare un record intestato a un altro utente significa assegnargli visibilità
e permessi di scrittura: è un'operazione da admin, e il gate è server-side.

## Le regole

1. **Il parametro va in query string, mai nel body.** Il body è il record e
   non ha allowlist: un `take_ownership` nel payload diventerebbe un dato del
   record.

   ```js
   // SÌ
   await fetch(`/import/${model}?take_ownership=true`, {
       method: "POST",
       headers: {"Content-Type": "application/json", ...authHeaders},
       body: JSON.stringify(record),
   });

   // NO — finisce nel record
   body: JSON.stringify({...record, take_ownership: true})
   ```

2. **Non spedire `owner_uid` sulle scritture normali.** Su
   `POST /{model}/{rec_name}` viene ignorato su update e sovrascritto con la
   sessione su insert. Vale per i flussi "duplica"/"salva come nuovo".

3. **Il 403 con `foreign_owner_requires_admin`.** Con `take_ownership=false`,
   se il payload porta un `owner_uid` diverso dall'utente corrente e
   l'utente non è admin:

   ```json
   {
     "detail": {
       "message": "Importing a record owned by another user requires admin; pass take_ownership=true to import it under your own uid",
       "reason": "foreign_owner_requires_admin",
       "model": "component"
     }
   }
   ```

   L'azione giusta lato UI: riproporre l'import con `take_ownership=true`,
   spiegando che i record verranno intestati all'utente corrente. Discrimina
   sul `reason`, non sul testo. Il `403` **non** scatta se il payload non ha
   `owner_uid`, se l'owner è già quello corrente, o se si passa
   `take_ownership=true`.

4. **Il 403 con `owner_uid_denied_by_field_acl`.** Se una `field_acl_policy`
   nega `owner_uid` in `create`, il campo viene scartato dal payload prima
   del gate e l'import con `take_ownership=false` fallisce. Nessun fallback
   silenzioso: l'owner diventa chi importa solo con `take_ownership=true` o
   con payload senza `owner_uid`.

5. **Gli altri `owner_*` non li decide il payload.** Con
   `take_ownership=false` sopravvive solo `owner_uid`: `owner_name`,
   `owner_mail`, `owner_sector`, ... vengono riletti dalla collection `user`
   locale per `uid`. Se l'uid non esiste localmente, l'import non fallisce —
   il record entra con l'`owner_uid` originale e gli altri `owner_*` vuoti.

6. **`id`/`_id` nel payload vengono scartati**: sono l'identità dell'istanza
   di origine. Il match dell'import resta su `rec_name` — reimportare lo
   stesso file aggiorna lo stesso record.

7. **L'ownership di un record esistente non è mai riassegnabile**: se il
   `rec_name` esiste già, l'import è un update e gli `owner_*` del payload
   vengono scartati, sempre, per chiunque.

## UI consigliata

Nel dialog di import, una singola scelta:

- **Mantieni gli autori originali** → `take_ownership=false` — solo per
  admin (`session.is_admin` è già disponibile da `GET /get_session`);
- **Importa a mio nome** → `take_ownership=true` — sempre disponibile.

Default: "mantieni" per gli admin, "a mio nome" per gli altri — così il 403
diventa un caso di bordo, non il flusso normale.