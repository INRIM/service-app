#!/usr/bin/env bash
# Documentazione locale di service-app (MkDocs Material, it+en).
# Uso:
#   ./run_docs.sh up       # avvia (o ricarica) il container docs
#   ./run_docs.sh down     # ferma il container
#   ./run_docs.sh build    # build statica in ./site
# Il sito serve su http://localhost:7800 con hot-reload dei sorgenti.
set -euo pipefail

COMPOSE_FILE="docker-compose.docs.yml"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

case "${1:-up}" in
  up)
    docker compose -f "$COMPOSE_FILE" up -d --build
    echo
    echo "Docs su http://localhost:7800 (hot-reload: modifica docs/ e aggiorna il browser)"
    docker compose -f "$COMPOSE_FILE" logs -f --tail 20 &
    trap 'kill $! 2>/dev/null' EXIT
    wait $!
    ;;
  down)
    docker compose -f "$COMPOSE_FILE" down
    ;;
  build)
    docker compose -f "$COMPOSE_FILE" run --rm --entrypoint sh docs \
      -c "pip install --quiet mkdocs-static-i18n && mkdocs build --strict --site-dir /docs/site"
    echo "Sito statico in ./site/"
    ;;
  *)
    echo "Uso: $0 {up|down|build}" >&2
    exit 1
    ;;
esac