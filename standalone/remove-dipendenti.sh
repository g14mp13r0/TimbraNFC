#!/bin/bash
# Elimina dipendenti per badge UID
# bash standalone/remove-dipendenti.sh 04F6E5D4C3B2 04A1B2C3D4E5 --yes

set -euo pipefail
APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$APP_DIR"
[ -f .env ] && set -a && source .env && set +a
exec "$APP_DIR/.venv/bin/python" "$APP_DIR/server/scripts/remove_dipendenti.py" "$@"
