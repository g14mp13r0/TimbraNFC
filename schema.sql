CREATE TABLE IF NOT EXISTS sedi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    codice TEXT UNIQUE NOT NULL,
    indirizzo TEXT,
    attiva INTEGER DEFAULT 1,
    creato_il DATETIME DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS dipendenti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cognome TEXT NOT NULL,
    badge_uid TEXT UNIQUE NOT NULL,
    email TEXT,
    reparto TEXT,
    sede_id INTEGER,
    attivo INTEGER DEFAULT 1,
    creato_il DATETIME DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (sede_id) REFERENCES sedi(id)
);

CREATE TABLE IF NOT EXISTS timbrature (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dipendente_id INTEGER NOT NULL,
    sede_id INTEGER,
    tipo TEXT CHECK(tipo IN ('entrata', 'uscita')) NOT NULL,
    timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
    sync_key TEXT UNIQUE,
    FOREIGN KEY (dipendente_id) REFERENCES dipendenti(id),
    FOREIGN KEY (sede_id) REFERENCES sedi(id)
);

CREATE TABLE IF NOT EXISTS utenti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    ruolo TEXT CHECK(ruolo IN ('admin', 'hr', 'lettura')) NOT NULL DEFAULT 'lettura',
    nome TEXT NOT NULL,
    attivo INTEGER DEFAULT 1,
    creato_il DATETIME DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS sync_coda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_key TEXT UNIQUE NOT NULL,
    tipo TEXT NOT NULL,
    payload TEXT NOT NULL,
    tentativi INTEGER DEFAULT 0,
    inviato_il DATETIME,
    creato_il DATETIME DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direzione TEXT NOT NULL,
    esito TEXT NOT NULL,
    dettagli TEXT,
    timestamp DATETIME DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS sync_meta (
    chiave TEXT PRIMARY KEY,
    valore TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    azione TEXT NOT NULL,
    entita TEXT NOT NULL,
    entita_id INTEGER,
    dettagli TEXT,
    utente TEXT DEFAULT 'sistema',
    timestamp DATETIME DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_timbrature_dipendente ON timbrature(dipendente_id);
CREATE INDEX IF NOT EXISTS idx_timbrature_timestamp ON timbrature(timestamp);
CREATE INDEX IF NOT EXISTS idx_timbrature_sede ON timbrature(sede_id);
CREATE INDEX IF NOT EXISTS idx_dipendenti_sede ON dipendenti(sede_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);

INSERT OR IGNORE INTO sedi (id, nome, codice, indirizzo) VALUES (1, 'Sede Principale', 'PRINCIPALE', NULL);
