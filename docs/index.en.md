---
title: Home
description: service-app — multi-tenant RAD backend with Form.io forms, generic MongoDB CRUD, AGID/Bootstrap Italia theme and Keycloak authentication.
---

# service-app

**service-app** is an open source (MIT) stack for building low-code
management applications: forms designed visually with **Form.io**, generic
CRUD on **MongoDB**, **AGID/Bootstrap Italia** theme and **Keycloak**
authentication.

<span class="mdx-badge">v3.0</span>
<span class="mdx-badge">MIT</span>
<span class="mdx-badge">multi-tenant</span>

The project is the merger of three pieces:

| Component | Repository | What it does |
|---|---|---|
| RAD backend | [`ozon-env-app`](https://github.com/INRIM/service-app) | Form.io, action router, 3-layer ACL, plugins, Camunda workers, companion services |
| Frontend | [`ozon-formio`](https://github.com/INRIM/ozon-formio) | Angular 20 + Form.io + AG Grid, Bootstrap Italia theme, single-origin reverse proxy |
| Executable demo | [`inrim-forms-demo`](https://github.com/INRIM/inrim-forms-demo) | Full stack in one command, sample plugin, 4 test users |

The official backend image is named `ozon-env-app`; the Python library that
provides the base for workers is
[`ozon-env`](https://github.com/archetipo/ozon-env) (also on
[PyPI](https://pypi.python.org/pypi/ozon-env)).

## Why this site

This is the **public** documentation of the service: architecture, quick
start, a **guided path** that takes you from "how do I create a form" to
**Camunda workers**, the deep-dive guides (ACL, security, import, remote
select) and an explanation of the executable demo with example modifications
to try.

## How the documentation is organized

- **[Getting started](getting-started.md)** — requirements and launching the demo in one command.
- **[Architecture](architecture.md)** — the stack pieces and how they talk to each other.
- **[Guided path](wizard/step-1-create-form.md)** — 5 steps: creating a form,
  the components, actions and groups, external services, workers and Camunda.
- **[Guides](guides/acl.md)** — deep dives: 3-layer ACL, Keycloak/BFF,
  query field ACL gate, import ownership, remote select, security.
- **[Demo](demo/index.md)** — how `inrim-forms-demo` is built and 3 example
  modifications to try.
- **[Reference](reference/action-router.md)** — API contracts: action router
  and endpoints.

## License

All project repositories are released under the
[MIT](https://github.com/INRIM/service-app/blob/3.0/LICENSE) license.