---
title: Sicurezza
description: Le scelte di sicurezza di service-app — BFF, cookie di sessione, boundary nginx, confini di fiducia e audit.
---

# Sicurezza

Riassunto delle scelte di sicurezza del progetto, con il risultato dell'audit
di sicurezza frontend (2026-07) su `ozon-app-web`: tutte le azioni del piano
d'azione risultano eseguite e verificate (246/246 test, build production,
build+run Docker reale).

## Modello auth: BFF, nessun token nel browser

- **Nessun token client-side**: cookie `ozon_session` httponly + `ozon_csrf`,
  header `X-CSRF-Token` sulle richieste mutanti. Nessun token in
  `localStorage`, in query string o nel bundle JS.
- `GET /get_session` espone solo `uid`/`username`/`authenticated`/`app_code`
  — mai token o claim JWT.
- Il WebSocket `/ws/actions` autentica sul cookie di sessione + controllo
  `Origin`; i token in query string non sono accettati.
- `authtoken`/`authToken`/`auth_token` nei payload non sono credenziali e
  vengono rimossi dal backend.
- Difesa in profondità: i test verificano che il frontend **non** adotti un
  token nemmeno se il backend lo invia per errore.

## Boundary nginx

Il nginx del web-client è il confine di rete:

- **azzera l'intera famiglia di header di identità** (`X-Forwarded-User`,
  `X-Auth-Request-*`, `X-Remote-Email/Groups`, ...) e inoltra solo
  `x-remote-user` — l'unico header di cui il backend si fida, e solo se
  iniettato nel boundary (verificato con test end-to-end con 11 header
  forgiati);
- non inoltra `Authorization` fabbricato dal client;
- aggiunge gli header di sicurezza: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy`,
  `Permissions-Policy` (CSP report-only pianificata come lavoro futuro).

Il container gira come utente **non privilegiato** (`USER nginx`, porta
interna 8080).

## Server-side

- **Query field ACL gate**: operatori allowlist su `query`/`order` +
  cross-check con l'ACL di campo (chiude la fuga di informazioni via filtri).
- **Remote select senza SSRF**: URL e header vivono solo sul component;
  il ramo `data.url` dal payload è stato rimosso (vedi
  [Select remote](remote-select.md)).
- **Fail-closed ovunque**: model ACL, record rules, action gate — dettagli in
  [ACL](acl.md).
- **Import ownership gated**: intestare un record a un altro utente è
  un'operazione da admin ([Import e ownership](import-ownership.md)).

## Confini di fiducia dichiarati

- **Il builder di form è un privilegio amministrativo.** La logica dei form
  Form.io è JavaScript: chi può scrivere uno schema di form ottiene
  esecuzione JS nel browser di chi lo apre.
- L'HTML degli editor WYSIWYG arriva sanificato (DOMPurify nega gli schemi
  URI `javascript:`/`data:`).
- SheetJS vendorizzato aggiornato a ≥0.20.2 (CVE-2023-30533, CVE-2024-22363
  non applicabili), con file di provenienza accanto al bundle.
- Le vulnerabilità note delle dipendenze di produzione sono state rientrate a
  una sola `low` residua (Quill, nessun fix upstream disponibile — mitigata
  dalla sanificazione dell'input prima del parse).

## Segreti nella demo

- I file versionati (`.env.demo`, `.env.client-demo`) sono template con
  segnaposto: **non ci vanno segreti veri**.
- `run_demo.sh` genera `MONGO_PASS`, `SESSION_SECRET`,
  `KEYCLOAK_ADMIN_PASSWORD` al primo avvio e li salva in `demo/.env.secrets`
  (gitignorato); i secret dei client Keycloak arrivano dal provisioning.
- Nessun segreto committato nella history (verificato con audit git).