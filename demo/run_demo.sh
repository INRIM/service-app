#!/usr/bin/env bash
# Avvia (o ferma) lo stack demo completo: keycloak + mongo + ozon-env-app +
# companion services + web-client, col plugin "demo" montato in /plugins/demo.
#
# Uso:
#   demo/run_demo.sh up      avvia tutto (default se nessun argomento)
#   demo/run_demo.sh down    ferma e rimuove i container (i volumi restano)
#   demo/run_demo.sh reset   come down, ma cancella anche i volumi (dati mongo/keycloak)
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$DEMO_DIR")"
cd "$ROOT_DIR"

PROJECT=ozon-demo
BACKEND_ARGS=(-p "$PROJECT" -f backend/docker-compose.yml -f demo/docker-compose.demo.yml --env-file demo/.env.demo)
CLIENT_ARGS=(-p "$PROJECT" -f app/docker-compose.client.example.yml --env-file demo/.env.client-demo)

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }

cmd="${1:-up}"

if [[ "$cmd" == "down" || "$cmd" == "reset" ]]; then
    step "Arresto web-client"
    docker compose "${CLIENT_ARGS[@]}" down 2>/dev/null || true
    step "Arresto backend stack"
    if [[ "$cmd" == "reset" ]]; then
        docker compose "${BACKEND_ARGS[@]}" down -v
    else
        docker compose "${BACKEND_ARGS[@]}" down
    fi
    echo "Fatto."
    exit 0
fi

if [[ "$cmd" != "up" ]]; then
    echo "Uso: $0 [up|down|reset]" >&2
    exit 1
fi

step "1/7 preparo backend/.env e app/.env dai template demo"
cp demo/.env.demo backend/.env
cp demo/.env.client-demo app/.env

step "2/7 avvio backend (keycloak + db + app + companion services)"
docker compose "${BACKEND_ARGS[@]}" up -d

# shellcheck disable=SC1091
set -a; source demo/.env.demo; set +a

step "3/7 attendo Keycloak (${KEYCLOAK_SERVER_URL_PUBLIC})"
for i in $(seq 1 60); do
    if curl -fs -o /dev/null "${KEYCLOAK_SERVER_URL_PUBLIC}/realms/master"; then
        break
    fi
    [[ $i -eq 60 ]] && { echo "Keycloak non risponde dopo 60 tentativi" >&2; exit 1; }
    sleep 2
done
echo "Keycloak pronto."

step "4/7 provisioning Keycloak (realm/client web + client M2M calendar-scheduler + utenti demo)"
# shellcheck disable=SC1091
set -a; source demo/.env.client-demo; set +a
PROVISION_OUT="$(demo/provision_keycloak.sh)"
echo "$PROVISION_OUT" >&2
SECRET="$(echo "$PROVISION_OUT" | grep '^KEYCLOAK_CLIENT_SECRET=' | cut -d= -f2-)"
SCHED_SECRET="$(echo "$PROVISION_OUT" | grep '^SCHEDULER_OAUTH_CLIENT_SECRET=' | cut -d= -f2-)"

sed -i.bak \
    -e "s/^KEYCLOAK_CLIENT_SECRET=.*/KEYCLOAK_CLIENT_SECRET=${SECRET}/" \
    -e "s/^SCHEDULER_OAUTH_CLIENT_SECRET=.*/SCHEDULER_OAUTH_CLIENT_SECRET=${SCHED_SECRET}/" \
    demo/.env.demo backend/.env
rm -f demo/.env.demo.bak backend/.env.bak

step "5/7 riavvio app + calendar-scheduler coi secret aggiornati"
docker compose "${BACKEND_ARGS[@]}" up -d --force-recreate app calendar-scheduler

for i in $(seq 1 60); do
    if curl -fs -o /dev/null -w '%{http_code}' "http://localhost:${OZON_APP_PORT:-7999}/login" | grep -q 302; then
        break
    fi
    [[ $i -eq 60 ]] && { echo "backend non risponde dopo 60 tentativi" >&2; exit 1; }
    sleep 2
done
echo "Backend pronto."

step "6/7 bootstrap plugin + gruppi demo (admin M2M, user/operator/manager)"
docker exec ozon-env-app uv run python bootstrap.py --admin admin
docker cp demo/seed_groups.py ozon-env-app:/app/seed_groups.py
docker exec ozon-env-app uv run python seed_groups.py

step "7/7 avvio web-client"
# --force-recreate: nginx risolve l'IP di "app" all'avvio e non lo aggiorna;
# se app e' stato ricreato allo step 5/7 con web-client gia' su, serve un
# riavvio anche qui altrimenti nginx resta agganciato all'IP vecchio (502).
docker compose "${CLIENT_ARGS[@]}" up -d --force-recreate

step "Demo pronta"
cat <<EOF

  Web app:   ${SITE_URL:-http://localhost:4200}
  Keycloak:  ${KEYCLOAK_SERVER_URL_PUBLIC} (admin / ${KEYCLOAK_ADMIN_PASSWORD})
  Backend:   http://localhost:${OZON_APP_PORT:-7999}

  Utenti demo (username = password): admin, user, operator, manager

  Stop:  demo/run_demo.sh down
  Reset: demo/run_demo.sh reset   (cancella anche i dati mongo/keycloak)
EOF
