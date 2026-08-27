---
title: Home
description: service-app — backend RAD multi-tenant con form Form.io, CRUD su MongoDB, tema AGID/Bootstrap Italia e autenticazione Keycloak.
---

# service-app

**service-app** è uno stack open source (MIT) per costruire applicazioni
gestionali a basso codice: form progettate visivamente con **Form.io**, CRUD
generico su **MongoDB**, tema **AGID/Bootstrap Italia** e autenticazione
**Keycloak**.

<span class="mdx-badge">v3.0</span>
<span class="mdx-badge">MIT</span>
<span class="mdx-badge">multi-tenant</span>

Il progetto nasce dalla fusione di tre pezzi:

| Componente | Repository | Cosa fa |
|---|---|---|
| Backend RAD | [`ozon-env-app`](https://github.com/INRIM/service-app) | Form.io, action router, ACL a 3 livelli, plugin, worker Camunda, companion service |
| Frontend | [`ozon-formio`](https://github.com/INRIM/ozon-formio) | Angular 20 + Form.io + AG Grid, tema Bootstrap Italia, reverse proxy single-origin |
| Demo eseguibile | [`inrim-forms-demo`](https://github.com/INRIM/inrim-forms-demo) | Stack completo in un comando, plugin di esempio, 4 utenti di test |

L'immagine ufficiale del backend si chiama `ozon-env-app`; la libreria
Python che fornisce la base ai worker è
[`ozon-env`](https://github.com/archetipo/ozon-env) (anche su
[PyPI](https://pypi.python.org/pypi/ozon-env)).

## Perché questo sito

Qui trovi la documentazione **pubblica** del servizio: architettura,
guida rapida, un **percorso guidato** che ti porta da «come creo un form»
ai **worker Camunda**, le guide approfondite (ACL, sicurezza, import,
select remote) e la spiegazione della demo eseguibile con esempi di
modifiche da provare.

## Come è organizzata la documentazione

- **[Iniziare](getting-started.md)** — requisiti e avvio della demo in un comando.
- **[Architettura](architecture.md)** — i pezzi dello stack e come parlano tra loro.
- **[Percorso guidato](wizard/step-1-create-form.md)** — 5 step: creare un form,
  i componenti, le action e i gruppi, i servizi esterni, i worker e Camunda.
- **[Guide](guides/acl.md)** — approfondimenti: ACL a 3 livelli, Keycloak/BFF,
  query field ACL gate, ownership dell'import, select remote, sicurezza.
- **[Demo](demo/index.md)** — com'è fatta `inrim-forms-demo` e 3 modifiche
  di esempio da provare.
- **[Riferimenti](reference/action-router.md)** — contratti API: action router
  ed endpoint.

## Licenza

Tutti i repository del progetto sono rilasciati con licenza
[MIT](https://github.com/INRIM/service-app/blob/3.0/LICENSE).