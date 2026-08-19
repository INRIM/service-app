#!/usr/bin/env bash
# Pulizia completa della demo: ferma e rimuove TUTTI i container, volumi
# e immagini (mongo, keycloak, scheduler), i container orfani del progetto, gli .env
# generati (backend/.env, app/.env) e riporta i secret in demo/.env.demo /
# demo/.env.client-demo a placeholder — cosi' la prossima demo/run_demo.sh up
# riparte identica a un checkout pulito.
#
# Diverso da "run_demo.sh reset" (che ferma solo cio' che e' definito nei
# compose correnti): questo rimuove anche eventuali container/volumi orfani
# rimasti da run precedenti con nomi/servizi diversi.
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$DEMO_DIR")"
cd "$ROOT_DIR"

PROJECT=ozon-demo
BACKEND_ARGS=(-p "$PROJECT" -f backend/docker-compose.yml -f demo/docker-compose.demo.yml --env-file demo/.env.demo)
CLIENT_ARGS=(-p "$PROJECT" -f app/docker-compose.client.example.yml --env-file demo/.env.client-demo)

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }

step "Arresto e rimuovo web-client (container + volumi + immagini + orfani)"
docker compose "${CLIENT_ARGS[@]}" down -v --rmi all --remove-orphans 2>/dev/null || true

step "Arresto e rimuovo backend (container + volumi + immagini + orfani)"
docker compose "${BACKEND_ARGS[@]}" down -v --rmi all --remove-orphans 2>/dev/null || true

step "Rimuovo eventuali container demo rimasti orfani per nome"
docker rm -f \
    ozon-env-app ozon-env-app-db ozon-env-keycloak \
    ozon-env-mail-sender ozon-env-calendar-scheduler ozon-env-identity-manager \
    demo-web 2>/dev/null || true

step "Rimuovo backend/.env e app/.env (rigenerati da run_demo.sh dai template demo)"
rm -f backend/.env app/.env

step "Riporto i secret in demo/.env.demo e demo/.env.client-demo a placeholder"
sed -i.bak \
    -e 's/^KEYCLOAK_CLIENT_SECRET=.*/KEYCLOAK_CLIENT_SECRET=change-me/' \
    -e 's/^SCHEDULER_OAUTH_CLIENT_SECRET=.*/SCHEDULER_OAUTH_CLIENT_SECRET=change-me/' \
    demo/.env.demo
rm -f demo/.env.demo.bak

echo
echo "Demo pulita. Per ripartire da zero: demo/run_demo.sh up"
