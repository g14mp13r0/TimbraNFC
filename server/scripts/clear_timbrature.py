#!/usr/bin/env python3
"""Elimina tutte le timbrature (server DB + coda locale kiosk)."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from server.app.db import SessionLocal
from server.app.services.timbrature_admin import clear_timbrature_locali, clear_timbrature_server


def main() -> int:
    parser = argparse.ArgumentParser(description="Azzera tutte le timbrature")
    parser.add_argument("--yes", action="store_true", help="Senza conferma interattiva")
    parser.add_argument("--server-only", action="store_true", help="Solo DB server")
    parser.add_argument("--local-only", action="store_true", help="Solo coda locale kiosk")
    args = parser.parse_args()

    if not args.yes:
        print("ATTENZIONE: eliminerà TUTTE le timbrature di TUTTI i dipendenti.")
        print("I dipendenti e i badge non vengono toccati.")
        risp = input('Digita AZZERA per confermare: ').strip()
        if risp != "AZZERA":
            print("Annullato.")
            return 1

    n_server = 0
    n_local = 0

    if not args.local_only:
        db = SessionLocal()
        try:
            n_server = clear_timbrature_server(db)
        finally:
            db.close()
        print(f"Server: eliminate {n_server} timbrature")

    if not args.server_only:
        try:
            import terminal.config as terminal_config

            n_local = clear_timbrature_locali(terminal_config.LOCAL_DB_PATH)
            print(f"Coda locale: eliminate {n_local} timbrature")
        except Exception as exc:
            print(f"Coda locale: saltata ({exc})")

    print("Fatto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
