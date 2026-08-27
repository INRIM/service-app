---
title: Security
description: service-app security choices — BFF, session cookies, nginx boundary, trust boundaries and audit.
---

# Security

Summary of the project's security choices, with the outcome of the frontend
security audit (2026-07) on `ozon-app-web`: all actions of the action plan
were executed and verified (246/246 tests, production build, real Docker
build+run).

## Auth model: BFF, no tokens in the browser

- **No client-side tokens**: `ozon_session` httponly cookie + `ozon_csrf`,
  `X-CSRF-Token` header on mutating requests. No token in `localStorage`, in
  query strings or in the JS bundle.
- `GET /get_session` exposes only `uid`/`username`/`authenticated`/`app_code`
  — never tokens or JWT claims.
- The `/ws/actions` WebSocket authenticates on the session cookie + `Origin`
  check; tokens in query strings are not accepted.
- `authtoken`/`authToken`/`auth_token` in payloads are not credentials and
  are stripped by the backend.
- Defense in depth: tests verify the frontend **does not** adopt a token even
  if the backend sends one by mistake.

## The nginx boundary

The web-client nginx is the network boundary:

- **blanks the entire identity-header family** (`X-Forwarded-User`,
  `X-Auth-Request-*`, `X-Remote-Email/Groups`, ...) and forwards only
  `x-remote-user` — the only header the backend trusts, and only if injected
  at the boundary (verified with an end-to-end test with 11 forged headers);
- does not forward client-forged `Authorization`;
- adds security headers: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`
  (report-only CSP planned as future work).

The container runs as an **unprivileged** user (`USER nginx`, internal port
8080).

## Server-side

- **Query field ACL gate**: operator allowlist on `query`/`order` +
  cross-check with the field ACL (closes the information leak via filters).
- **Remote select without SSRF**: URLs and headers live only on the
  component; the `data.url` payload branch was removed (see
  [Remote selects](remote-select.md)).
- **Fail-closed everywhere**: model ACL, record rules, action gate — details
  in [ACL](acl.md).
- **Import ownership gated**: owning a record to another user is an admin
  operation ([Import and ownership](import-ownership.md)).

## Declared trust boundaries

- **The form builder is an administrative privilege.** Form.io form logic is
  JavaScript: whoever can write a form schema gets JS execution in the
  browser of whoever opens it.
- WYSIWYG editor HTML arrives sanitized (DOMPurify denies `javascript:`/
  `data:` URI schemes).
- The vendored SheetJS was upgraded to ≥0.20.2 (CVE-2023-30533, CVE-2024-22363
  no longer applicable), with a provenance file next to the bundle.
- Known production-dependency vulnerabilities were reduced to a single
  residual `low` (Quill, no upstream fix available — mitigated by sanitizing
  input before parsing).

## Secrets in the demo

- The versioned files (`.env.demo`, `.env.client-demo`) are templates with
  placeholders: **never put real secrets in them**.
- `run_demo.sh` generates `MONGO_PASS`, `SESSION_SECRET`,
  `KEYCLOAK_ADMIN_PASSWORD` on first startup and saves them to
  `demo/.env.secrets` (gitignored); Keycloak client secrets come from the
  provisioning.
- No secret ever committed to history (verified with a git audit).