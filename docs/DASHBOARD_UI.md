# TimbraNFC — Template grafica corporate (dashboard admin)

Questo pacchetto contiene i template Jinja2 + CSS pronti da innestare nel
progetto FastAPI esistente, basati sulla grafica corporate sobria
(navy/grigio) approvata nel mockup.

## Cosa contiene

```
templates/
  base.html                  ← layout condiviso (sidebar, topbar, breadcrumb)
  index.html                 ← NUOVA pagina Dashboard (prima non esisteva)
  dipendenti.html            ← sostituisce il file originale
  dipendente_modifica.html   ← sostituisce il file originale
  dipendente_badge.html      ← sostituisce il file originale
  timbrature.html            ← sostituisce il file originale
  report.html                ← sostituisce il file originale
  dispositivi.html           ← sostituisce il file originale

static/
  style.css                  ← NUOVO file, design system completo
  enrollment.js              ← ricostruito (vedi nota sotto, IMPORTANTE)

main.py                      ← versione patchata del tuo main.py originale
```

## Installazione

1. Copia tutto il contenuto di `templates/` nella cartella
   `server/app/templates/` del progetto (sovrascrivi i file esistenti).
2. Copia tutto il contenuto di `static/` nella cartella
   `server/app/static/` del progetto.
3. Sostituisci `server/app/main.py` con il file `main.py` incluso qui,
   **oppure** applica manualmente le differenze (vedi sotto "Modifiche a
   main.py") se nel frattempo hai modificato il file originale.
4. Riavvia il server (`uvicorn` / processo systemd) e ricarica la pagina:
   font Google (Source Serif 4, Inter, JetBrains Mono) vengono caricati
   da `fonts.googleapis.com`, serve quindi connessione internet sul
   client che apre la dashboard (non sul Raspberry Pi terminale).

## Modifiche a main.py

Il file `main.py` incluso è il tuo originale con **solo queste aggiunte**,
nessuna logica di business toccata:

- Ogni `templates.TemplateResponse(...)` ora passa anche `"active_page"`
  (per evidenziare la voce corretta nella sidebar) e, dove sensato,
  `"sidebar_n_dip"` / `"sidebar_n_timb"` / `"sidebar_n_dev"` (per i
  contatori numerici accanto alle voci di menu).
- Nessuna route, nessun modello, nessun import è stato modificato.

Se preferisci non sostituire il file, cerca nel tuo `main.py` ogni
`templates.TemplateResponse(...)` e aggiungi manualmente le chiavi sopra
indicate al dizionario di contesto, confrontando con la versione inclusa.

## ⚠️ enrollment.js — DA VERIFICARE

Il progetto che hai condiviso referenzia `static/enrollment.js` nelle pagine
`dipendenti.html` e `dipendente_badge.html`, ma quel file **non era incluso**
tra i file caricati, e nemmeno il contratto del relativo `enrollment_api`
(router già importato in `main.py` come `enrollment_api`, ma il suo
contenuto non è stato fornito).

Ho ricostruito un `enrollment.js` plausibile con un pattern standard
start/poll/stop:

- `POST /api/enrollment/start` → avvia la sessione di lettura badge
- `GET  /api/enrollment/status?session_id=...` → polling dello stato
- `POST /api/enrollment/stop` → ferma la sessione

**Prima di usarlo in produzione**, apri `server/app/api/enrollment.py` (o
dove si trova il router `enrollment_api`) e verifica che i path e i nomi
dei campi JSON coincidano con quelli reali. Se sono diversi, modifica solo
le 3 costanti in cima a `enrollment.js`:

```js
const API_START = "/api/enrollment/start";
const API_STATUS = "/api/enrollment/status";
const API_STOP = "/api/enrollment/stop";
```

La logica di interazione con `badge_uid` (id input), `btn-enroll`,
`btn-submit` ed `enroll-status` è invece coerente al 100% con l'HTML
delle pagine `dipendenti.html` / `dipendente_badge.html` incluse qui.

## Novità rispetto all'originale

- **Dashboard** (`/`, `index.html`): pagina che prima non esisteva,
  KPI principali + ultime timbrature + stato flotta.
- **Filtri aggiuntivi** lato client (non richiedono modifiche al backend
  oltre a quelle già presenti):
  - Dipendenti: ricerca testo libero + filtro reparto + filtro stato
  - Timbrature: chip filtro reparto (oltre ai filtri server-side esistenti)
  - Dispositivi: ricerca testo libero + filtro stato online/offline
- **Timeline turno**: nel Report turni, ogni riga mostra entrata→uscita
  come linea con pallini colorati (verde=entrata, rosso=uscita, ambra
  tratteggiato=turno ancora aperto) invece delle sole colonne testuali.
- **KPI card** su Dashboard e Dispositivi (online/offline/totale).

## Compatibilità conservata

Tutte le route, i nomi dei campi form (`nome`, `cognome`, `badge_uid`,
`reparto`, `email`, `confirm`, ecc.), gli endpoint POST/GET e i parametri
query (`msg`, `error`, `da`, `a`, `mese`, `dipendente_id`) sono identici
all'originale: il backend non richiede altre modifiche oltre a quelle
indicate sopra per `active_page`/contatori sidebar.
