# Deploy TimbraNFC Server su Proxmox CT

Guida per installare il **server di sede** in un container LXC su Proxmox VE.
I terminali Raspberry Pi si collegano a questo CT via LAN.

---

## 1. Creare il CT su Proxmox

### Parametri consigliati

| Parametro | Valore |
|-----------|--------|
| Template | Debian 12 o Ubuntu 22.04 |
| CPU | 1 core |
| RAM | 1024–2048 MB |
| Disco | 8–16 GB |
| Rete | bridge `vmbr0`, IP statico LAN |
| Tipo | CT non privilegiato (ok) |

### IP statico (esempio)

In Proxmox → CT → Network, oppure in `/etc/network/interfaces` nel CT:

```
address 192.168.1.50/24
gateway 192.168.1.1
```

Annota l'IP: i terminali useranno `SERVER_URL=http://192.168.1.50`

### Firewall Proxmox (se attivo)

Apri dal LAN verso il CT:
- **TCP 80** (HTTP / nginx)
- **TCP 443** (HTTPS, opzionale)
- **TCP 8000** solo se esponi uvicorn direttamente (non necessario con nginx)

---

## 2. Installazione automatica

Entra nel CT come root:

```bash
apt update && apt install -y git curl
git clone https://github.com/g14mp13r0/TimbraNFC.git /opt/timbranfc
cd /opt/timbranfc
bash server/scripts/install-proxmox-ct.sh
```

Lo script installa:
- MariaDB + database `timbranfc`
- Python venv + dipendenze
- Seed dati iniziali
- systemd `timbranfc-server`
- nginx reverse proxy

Al termine stampa **IP**, **API_KEY** e credenziali dashboard.

---

## 3. Installazione manuale (alternativa)

```bash
apt install -y python3 python3-venv mariadb-server nginx git
systemctl enable --now mariadb

mysql -e "CREATE DATABASE timbranfc; CREATE USER 'timbranfc'@'localhost' IDENTIFIED BY 'TUA_PASSWORD'; GRANT ALL ON timbranfc.* TO 'timbranfc'@'localhost';"

git clone https://github.com/g14mp13r0/TimbraNFC.git /opt/timbranfc
cd /opt/timbranfc
python3 -m venv .venv
.venv/bin/pip install -r requirements-server.txt

cp .env.example .env
# Modifica DATABASE_URL, API_KEY, ADMIN_PASSWORD

.venv/bin/python server/scripts/seed.py
# systemd + nginx come nello script
```

---

## 4. Configurare i terminali Raspberry

Sul CT, leggi l'API key:

```bash
grep API_KEY /opt/timbranfc/.env
```

Sul Raspberry (`/opt/timbranfc/.env` o variabili systemd):

```ini
SERVER_URL=http://192.168.1.50
API_KEY=la-stessa-chiave-del-server
SYNC_INTERVAL_SEC=30
DISPLAY_WIDTH=480
DISPLAY_HEIGHT=320
```

Riavvia il terminale:

```bash
sudo systemctl restart timbranfc-terminal
```

Verifica dalla dashboard del CT: **Dispositivi** → terminale online dopo ~1 min (heartbeat).

---

## 5. HTTPS (consigliato in produzione)

Certificato self-signed (LAN interna):

```bash
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /etc/ssl/private/timbranfc.key \
  -out /etc/ssl/certs/timbranfc.crt \
  -subj "/CN=timbranfc.local"

# Usa server/nginx/timbranfc.conf come base
cp /opt/timbranfc/server/nginx/timbranfc.conf /etc/nginx/sites-available/timbranfc
nginx -t && systemctl reload nginx
```

Sui terminali: `SERVER_URL=https://192.168.1.50` (potrebbe servire `verify=False` in dev o certificato trusted).

---

## 6. Backup

Backup giornaliero consigliato:

```bash
# Dump DB
mysqldump timbranfc > /backup/timbranfc-$(date +%F).sql

# Snapshot CT da Proxmox (metodo più semplice)
# Proxmox UI → CT → Backup → Snapshot
```

---

## 7. Troubleshooting

| Problema | Soluzione |
|----------|-----------|
| Terminali offline | `ping` CT da Pi; verificare `SERVER_URL` e firewall |
| Sync fallisce | Controllare `API_KEY` uguale su server e terminale |
| 502 nginx | `systemctl status timbranfc-server` — uvicorn non attivo |
| MariaDB non parte in CT | Verificare risorse CT; `journalctl -u mariadb` |

Log server:

```bash
journalctl -u timbranfc-server -f
```

---

## 8. Aggiornamenti

```bash
cd /opt/timbranfc
git pull
.venv/bin/pip install -r requirements-server.txt
systemctl restart timbranfc-server
```
