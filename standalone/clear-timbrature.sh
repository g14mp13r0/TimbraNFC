#!/bin/bash
# Azzera tutte le timbrature (server + coda locale kiosk)
# bash standalone/clear-timbrature.sh
# bash standalone/clear-timbrature.sh --yes   # senza prompt

set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$APP_DIR"

if [ -f "$APP_DIR/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$APP_DIR/.env"
    set +a
fi

export STANDALONE="${STANDALONE:-1}"
export TIMBRANFC_DATA="${TIMBRANFC_DATA:-$APP_DIR/data}"

PY="$APP_DIR/.venv/bin/python"
if [ ! -x "$PY" ]; then
    PY=python3
fi

exec "$PY" "$APP_DIR/server/scripts/clear_timbrature.py" "$@"
