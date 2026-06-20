# Deploy standalone — un solo Raspberry Pi

Un Raspberry fa **tutto**:
- **Touchscreen** → solo timbratrice (badge NFC + pulsanti IT/IP/FP/FT)
- **Server interno** → dashboard e API accessibili da altri PC via browser

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi                          │
│                                                          │
│  ┌──────────────┐         ┌─────────────────────────┐   │
│  │ Touchscreen  │         │  Server :8080 (LAN)      │   │
│  │ Kiosk        │──local──│  Dashboard + SQLite      │   │
│  │ (timbratrice)│         │  Dipendenti, report…     │   │
│  └──────────────┘         └───────────┬─────────────┘   │
│         NFC USB                       │                  │
└───────────────────────────────────────┼──────────────────┘
                                        │ http://IP:8080
                              ┌─────────▼─────────┐
                              │  PC / tablet HR   │
                              │  (solo browser)   │
                              └───────────────────┘
```

---

## Installazione rapida

```bash
curl -sL https://github.com/g14mp13r0/TimbraNFC/raw/main/standalone/install-raspberry.sh | sudo bash
```

Oppure manualmente:

```bash
git clone https://github.com/g14mp13r0/TimbraNFC.git /home/pi/TimbraNFC
cd /home/pi/TimbraNFC
sudo bash standalone/install-raspberry.sh
```

---

## Servizi systemd

| Servizio | Ruolo | Avvio |
|----------|-------|-------|
| `timbranfc-server` | API + dashboard web | Automatico al boot |
| Kiosk UI | Timbratrice NFC touchscreen | Autologin desktop + autostart |

```bash
sudo systemctl status timbranfc-server
bash standalone/verify-kiosk.sh
tail -f /tmp/timbranfc-kiosk.log
```

### Avvio automatico kiosk (senza login)

Dopo l'installazione, configura autologin e autostart:

```bash
cd ~/TimbraNFC
sudo bash standalone/setup-boot-kiosk.sh
sudo reboot
```

Al boot il Pi entra da solo nel desktop e avvia `kiosk_ui` (~30 secondi). Nessuna password sul touchscreen.

Se il kiosk non parte:

```bash
sudo bash standalone/fix-services.sh    # server + autologin + autostart
sudo reboot
```

Il kiosk **non apre mai** la dashboard: è riservato al touchscreen per le timbrature.

---

## Accesso dashboard da altro PC

1. Trova l'IP del Raspberry: `hostname -I`
2. Da un PC sulla stessa rete: **http://192.168.x.x:8080**
3. Gestisci dipendenti, vedi dispositivo, report

Credenziali default: `admin@local` / `admin` (modificare in `.env`).

---

## Configurazione `.env`

```bash
cp .env.standalone.example .env
nano .env
```

Variabili principali:

| Variabile | Descrizione |
|-----------|-------------|
| `SERVER_PORT` | Porta dashboard (default 8080) |
| `DISPLAY_WIDTH/HEIGHT` | Risoluzione touchscreen (480×320) |
| `MOCK_NFC=1` | Test senza lettore NFC |
| `TIMBRANFC_DATA` | Cartella dati SQLite |

---

## Flusso timbratura

1. Dipendente avvicina badge → kiosk mostra pulsanti validi
2. Timbratura scritta in coda locale (`data/local_queue.db`)
3. Sync immediata verso server locale (`data/timbranfc.db`)
4. Visibile subito in dashboard da PC

Se il server si riavvia, la coda locale ritenta automaticamente.

---

## Hardware consigliato

- Raspberry Pi 4/5
- Touchscreen SPI 3.5" (480×320)
- ACR122U NFC USB
- LED + buzzer (opzionale, GPIO)

Calibrare touch una tantum:

```bash
xinput_calibrator
```

---

## Architetture non usate in standalone

- **Proxmox CT** → non necessario
- **Sync remoto multi-sede** → disabilitato (`STANDALONE=1`)
- **Dashboard sul touchscreen** → non prevista by design

Per multi-sede o server centralizzato, vedere `docs/DEPLOY_PROXMOX.md` (deploy opzionale).
