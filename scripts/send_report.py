#!/usr/bin/env python3
"""Invia il report mensile via email. Usabile da cron o systemd timer."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from notifications import invia_report_mensile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Invia report presenze mensile via email")
    parser.add_argument("--mese", type=int, help="Mese (1-12), default: mese precedente")
    parser.add_argument("--anno", type=int, help="Anno, default: corrente")
    args = parser.parse_args()

    from datetime import date

    oggi = date.today()
    mese = args.mese
    anno = args.anno or oggi.year
    if mese is None:
        if oggi.month == 1:
            mese, anno = 12, oggi.year - 1
        else:
            mese = oggi.month - 1

    ok = invia_report_mensile(anno, mese)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
