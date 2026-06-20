# Installazione da PC con micro SD collegata (adattatore USB)

Guida per preparare la SD **prima** di inserirla nel Raspberry Pi.

---

## Prerequisiti

1. **Raspberry Pi OS** già flashato sulla SD (Desktop consigliato per il touchscreen)
   - Se la SD è vuota: usa [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
   - Utente: `pi`, password a tua scelta
   - Configura WiFi/Ethernet già dall'Imager se possibile

2. SD collegata al PC via adattatore USB

---

## Passo 1 — Identifica la SD

Apri un terminale:

```bash
lsblk
```

Cerca un disco nuovo (es. `sdb`), tipicamente **2 partizioni**:
- `sdb1` — boot (vfat/FAT32), ~256 MB–512 MB
- `sdb2` — root (ext4), resto dello spazio

⚠️ **Controlla bene la lettera** (`sdb`, `sdc`…) per non formattare il disco sbagliato.

---

## Passo 2 — Monta le partizioni

```bash
sudo mkdir -p /mnt/rpi-boot /mnt/rpi-root
sudo mount /dev/sdb1 /mnt/rpi-boot    # sostituisci sdb con il tuo disco
sudo mount /dev/sdb2 /mnt/rpi-root
```

Su alcune distro la root si monta automaticamente in `/media/tuo-utente/rootfs`.

---

## Passo 3 — Copia e prepara TimbraNFC

Dal PC, nella cartella del progetto clonato:

```bash
cd /home/gpastorino/Programmazione/TimbraNFC
sudo bash standalone/install-on-sd.sh /mnt/rpi-root /mnt/rpi-boot
```

Lo script:
- Copia il progetto in `/home/pi/TimbraNFC` sulla SD
- Abilita **SSH** al boot (file `ssh` nella partizione boot)
- Programma l'installazione completa al **primo avvio** del Pi

---

## Passo 4 — Smonta in sicurezza

```bash
sync
sudo umount /mnt/rpi-boot /mnt/rpi-root
```

Poi espelli la SD e inseriscila nel Raspberry.

---

## Passo 5 — Primo avvio del Raspberry

1. Collega **Ethernet** (consigliato la prima volta) o WiFi già configurato
2. Collega touchscreen, NFC USB, alimentazione
3. Attendi **5–10 minuti** (installazione automatica: pip, systemd, servizi)

Verifica dal Pi (SSH o tastiera+monitor HDMI):

```bash
sudo systemctl status timbranfc-server timbranfc-kiosk
hostname -I
```

---

## Accesso

| Cosa | Dove |
|------|------|
| Timbratrice | Touchscreen del Pi (kiosk) |
| Dashboard admin | `http://<IP-RASPBERRY>:8080` da un **altro PC** |
| SSH | `ssh pi@<IP-RASPBERRY>` |

Credenziali default dashboard: `admin@local` / `admin`

---

## Alternativa: installazione con Pi già acceso

Se preferisci non preparare la SD da PC:

```bash
ssh pi@<IP-RASPBERRY>
git clone https://github.com/g14mp13r0/TimbraNFC.git /home/pi/TimbraNFC
cd /home/pi/TimbraNFC
sudo bash standalone/install-raspberry.sh
```

---

## Problemi comuni

| Problema | Soluzione |
|----------|-----------|
| SD non vista (`0 B`) | Riprova adattatore/porta USB; prova `sudo lsblk` |
| Permesso negato | Usa sempre `sudo` per montare |
| First-boot fallisce | `journalctl -u timbranfc-firstboot`; serve rete per `apt`/`pip` |
| Kiosk non parte | Serve desktop attivo: `sudo systemctl start timbranfc-kiosk` |
| NFC non legge | `sudo systemctl status pcscd` |

---

## Installazione completa in chroot (avanzato, opzionale)

Se sul PC hai `qemu-user-static`:

```bash
sudo apt install qemu-user-static
sudo bash standalone/install-on-sd.sh /mnt/rpi-root /mnt/rpi-boot
```

In questo caso l'installazione può completarsi **subito sulla SD**, senza attendere il primo boot.
