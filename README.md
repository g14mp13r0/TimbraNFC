# TimbraNFC v2 — Architettura terminal/server

## Struttura

```
terminal/     → Raspberry Pi (NFC + display 3.5" + coda offline)
server/       → Mini PC sede (FastAPI + MySQL + dashboard)
shared/       → Schemi Pydantic API
docs/         → Specifiche tecniche
```

## Quick start (sviluppo)

```bash
# Server
pip install -r requirements-server.txt
python server/scripts/seed.py
DATABASE_URL=sqlite:///./server/data/timbranfc.db python -m uvicorn server.app.main:app --reload

# Terminale (mock NFC/GUI)
pip install -r requirements-terminal.txt
SERVER_URL=http://127.0.0.1:8000 MOCK_NFC=1 python terminal/main.py
```

## Produzione

### Server di sede
1. Installare MySQL, creare DB `timbranfc`
2. `DATABASE_URL=mysql+pymysql://user:pass@localhost/timbranfc`
3. `alembic -c server/migrations/alembic.ini upgrade head`
4. Copiare `server/systemd/timbranfc-server.service` e `server/nginx/timbranfc.conf`

### Terminale
1. Copiare `.env.example` → `.env`
2. Impostare `SERVER_URL`, `API_KEY`, `SEDE_ID`
3. `sudo cp terminal/systemd/timbranfc-terminal.service /etc/systemd/system/`
4. Calibrare touch: `xinput_calibrator`

## Provisioning nuovo terminale
1. Avviare terminale → genera `device_uuid` automaticamente
2. Registrazione via `POST /api/v1/devices/register`
3. Pull anagrafica automatico da sync_agent
4. Assegnare nome dispositivo da dashboard → Dispositivi

## Legacy

I file in root (`main.py`, `dashboard/`, `sync.py`…) sono la v1 deprecata.
