# TimbraNFC — Timbratrice standalone su Raspberry Pi

Un solo Raspberry Pi: **timbratrice NFC** sul touchscreen + **dashboard web** accessibile da altri PC in rete.

```
Touchscreen Pi  →  solo timbratura (IT / IP / FP / FT)
PC in LAN       →  http://<ip-raspberry>:8080  (admin, report, dipendenti)
```

## Installazione (Raspberry Pi)

```bash
git clone https://github.com/g14mp13r0/TimbraNFC.git /home/pi/TimbraNFC
cd /home/pi/TimbraNFC
sudo bash standalone/install-raspberry.sh
```

Guida completa: [docs/DEPLOY_STANDALONE.md](docs/DEPLOY_STANDALONE.md)

## Sviluppo su PC

```bash
pip install -r requirements-server.txt -r requirements-terminal.txt
cp .env.standalone.example .env

# Terminale 1 — server
python standalone/run_server.py

# Terminale 2 — kiosk (mock NFC)
MOCK_NFC=1 python standalone/run_kiosk.py
```

Dashboard: http://localhost:8080

## Struttura

```
standalone/     → installazione Pi, run_server.py, run_kiosk.py, script manutenzione
terminal/       → kiosk UI, NFC, coda locale, sync
server/         → FastAPI + dashboard web (Jinja2)
shared/         → i18n, schemi API, calcolo turni, date
docs/           → guide deploy e specifica tecnica
data/           → SQLite runtime (timbranfc.db + local_queue.db)
```

## Deploy alternativi (opzionali)

- [Multi-sede con server Proxmox](docs/DEPLOY_PROXMOX.md) — non necessario per standalone
