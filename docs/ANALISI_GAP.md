# Analisi gap — Repo vs Spec (Sez. 1)

**Data analisi:** Giugno 2026

## Differenze rilevate

| Spec (Sez. 1) | Repo reale | Azione |
|---|---|---|
| Path `/home/pi/timbratrice/` | `/home/gpastorino/Programmazione/TimbraNFC/` | Nuova struttura `terminal/` + `server/` |
| `stati.py` abbozzo IT/IP/FP/FT | **Assente** | Creare da zero (Sez. 3) |
| `main.py` FastAPI + SQLite locale | Evoluto: hub sync, ruoli, multi-sede | Sostituire con architettura terminal/server |
| `ui_kiosk.py` 800×480, poll API | Font 72px, poll `/api/last-event` | Riscrivere `kiosk_ui.py` 480×320, 4 pulsanti |
| `presenze.db` unico DB | Schema esteso (utenti, sync_coda, audit…) | Terminale: `local_queue.db`; Server: MySQL |
| Dashboard Flask → stesso SQLite | Flask con sedi, utenti, sync page | Consolidare su FastAPI server + MySQL |
| Nessun sync/OTA/heartbeat | `sync.py` hub model (diverso da spec) | Nuovo `sync_agent.py` + contratti Sez. 5 |
| Alternanza entrata/uscita | `timbratura.py` alternanza auto | Macchina stati 4 azioni |

## File legacy (root) — deprecati dopo refactor

I moduli in root (`main.py`, `ui_kiosk.py`, `sync.py`, `dashboard/`, …) restano fino al cutover;
il deploy target usa solo `terminal/` e `server/`.
