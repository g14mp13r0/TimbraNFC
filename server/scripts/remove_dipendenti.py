#!/usr/bin/env python3
"""Elimina dipendenti per badge UID (e le loro timbrature)."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from server.app.db import SessionLocal
from server.app.models import Dipendente, Timbratura


def main() -> int:
    parser = argparse.ArgumentParser(description="Elimina dipendenti per badge UID")
    parser.add_argument("badge_uids", nargs="+", help="UID badge (es. 04A1B2C3D4E5)")
    parser.add_argument("--yes", action="store_true", help="Senza conferma")
    args = parser.parse_args()

    uids = [u.strip().upper() for u in args.badge_uids]
    if not args.yes:
        print("Eliminerà dipendenti e TUTTE le loro timbrature:")
        for u in uids:
            print(f"  - {u}")
        if input("Digita SI per confermare: ").strip().upper() != "SI":
            print("Annullato.")
            return 1

    db = SessionLocal()
    try:
        for uid in uids:
            dip = db.query(Dipendente).filter(Dipendente.badge_uid == uid).first()
            if not dip:
                print(f"Non trovato: {uid}")
                continue
            n_t = db.query(Timbratura).filter(Timbratura.dipendente_id == dip.id).delete()
            nome = f"{dip.nome} {dip.cognome}"
            db.delete(dip)
            print(f"Eliminato {nome} ({uid}) — {n_t} timbrature")
            try:
                from terminal import local_queue

                if local_queue.remove_dipendente(uid):
                    print(f"  Cache kiosk: rimosso {uid}")
            except Exception:
                pass
        db.commit()
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
