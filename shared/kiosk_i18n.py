"""Testi multilingua kiosk + dashboard web (it, fr, en)."""

from __future__ import annotations

import os

Lang = str

_DEFAULT_LANG = "it"
_SUPPORTED = frozenset({"it", "fr", "en"})

_STRINGS: dict[str, dict[Lang, str]] = {
    # --- Web: navigazione ---
    "brand_tag": {
        "it": "Pannello Admin",
        "fr": "Panneau Admin",
        "en": "Admin Panel",
    },
    "nav_overview": {"it": "Panoramica", "fr": "Vue d'ensemble", "en": "Overview"},
    "nav_presences": {"it": "Presenze", "fr": "Présences", "en": "Attendance"},
    "nav_directory": {"it": "Anagrafica", "fr": "Annuaire", "en": "Directory"},
    "nav_system": {"it": "Sistema", "fr": "Système", "en": "System"},
    "nav_dashboard": {"it": "Dashboard", "fr": "Tableau de bord", "en": "Dashboard"},
    "nav_timbrature": {"it": "Timbrature", "fr": "Pointages", "en": "Clock events"},
    "nav_report": {"it": "Report turni", "fr": "Rapport postes", "en": "Shift report"},
    "nav_dipendenti": {"it": "Dipendenti", "fr": "Employés", "en": "Employees"},
    "nav_dispositivi": {"it": "Dispositivi", "fr": "Terminaux", "en": "Devices"},
    "nav_impostazioni": {"it": "Impostazioni", "fr": "Paramètres", "en": "Settings"},
    "role_admin": {"it": "Amministratore", "fr": "Administrateur", "en": "Administrator"},
    "devices_online_title": {
        "it": "Stato dispositivi in linea",
        "fr": "État des terminaux en ligne",
        "en": "Online device status",
    },
    # --- Web: dashboard ---
    "home_greeting": {
        "it": "Buongiorno, Amministratore",
        "fr": "Bonjour, Administrateur",
        "en": "Good morning, Administrator",
    },
    "home_subtitle": {
        "it": "Riepilogo di Sede Principale — aggiornato in tempo reale",
        "fr": "Résumé du site principal — mis à jour en temps réel",
        "en": "Main site summary — updated in real time",
    },
    "kpi_active_employees": {
        "it": "Dipendenti attivi",
        "fr": "Employés actifs",
        "en": "Active employees",
    },
    "kpi_stamps_today": {
        "it": "Timbrature registrate oggi",
        "fr": "Pointages aujourd'hui",
        "en": "Clock events today",
    },
    "kpi_terminals": {
        "it": "Terminali registrati",
        "fr": "Terminaux enregistrés",
        "en": "Registered terminals",
    },
    "kpi_recent_events": {
        "it": "Eventi recenti mostrati",
        "fr": "Événements récents affichés",
        "en": "Recent events shown",
    },
    "today_label": {"it": "oggi", "fr": "aujourd'hui", "en": "today"},
    "recent_stamps": {"it": "Ultime timbrature", "fr": "Derniers pointages", "en": "Latest clock events"},
    "see_all": {"it": "Vedi tutte →", "fr": "Voir tout →", "en": "See all →"},
    "no_stamps": {
        "it": "Nessuna timbratura registrata",
        "fr": "Aucun pointage enregistré",
        "en": "No clock events recorded",
    },
    "shift_start": {"it": "Inizio", "fr": "Début", "en": "Start"},
    "shift_end": {"it": "Fine", "fr": "Fin", "en": "End"},
    # --- Web: impostazioni ---
    "settings_title": {"it": "Impostazioni", "fr": "Paramètres", "en": "Settings"},
    "settings_subtitle": {
        "it": "Configura kiosk, rete, sicurezza e backup. Usa «Salva e riavvia kiosk» per applicare subito le modifiche al touchscreen.",
        "fr": "Configurez le kiosk, le réseau, la sécurité et la sauvegarde. Utilisez « Enregistrer et redémarrer le kiosk » pour appliquer les changements à l'écran.",
        "en": "Configure kiosk, network, security and backup. Use «Save and restart kiosk» to apply touchscreen changes immediately.",
    },
    "settings_saved": {
        "it": "Impostazioni salvate in",
        "fr": "Paramètres enregistrés dans",
        "en": "Settings saved to",
    },
    "settings_saved_restart": {
        "it": "Impostazioni salvate e kiosk in riavvio.",
        "fr": "Paramètres enregistrés et redémarrage du kiosk.",
        "en": "Settings saved and kiosk restarting.",
    },
    "settings_restart_failed": {
        "it": "Impostazioni salvate, ma riavvio kiosk fallito:",
        "fr": "Paramètres enregistrés, mais échec du redémarrage du kiosk :",
        "en": "Settings saved, but kiosk restart failed:",
    },
    "settings_bg_updated": {
        "it": "Sfondo kiosk aggiornato.",
        "fr": "Fond d'écran du kiosk mis à jour.",
        "en": "Kiosk background updated.",
    },
    "settings_bg_error": {
        "it": "Caricamento sfondo fallito — usa un file PNG valido.",
        "fr": "Échec du téléchargement — utilisez un PNG valide.",
        "en": "Background upload failed — use a valid PNG file.",
    },
    "settings_bg_title": {
        "it": "Sfondo kiosk",
        "fr": "Fond d'écran kiosk",
        "en": "Kiosk background",
    },
    "settings_bg_sub": {
        "it": "Logo o immagine mostrata sul touchscreen timbratrice",
        "fr": "Logo ou image affichée sur l'écran tactile",
        "en": "Logo or image shown on the clock-in touchscreen",
    },
    "settings_bg_none": {
        "it": "Nessuno sfondo personalizzato",
        "fr": "Aucun fond personnalisé",
        "en": "No custom background",
    },
    "settings_bg_current": {
        "it": "File attuale:",
        "fr": "Fichier actuel :",
        "en": "Current file:",
    },
    "settings_bg_upload": {
        "it": "Carica nuovo sfondo (PNG)",
        "fr": "Télécharger un fond (PNG)",
        "en": "Upload new background (PNG)",
    },
    "settings_bg_submit": {
        "it": "Carica sfondo",
        "fr": "Télécharger le fond",
        "en": "Upload background",
    },
    "settings_save": {
        "it": "Salva impostazioni",
        "fr": "Enregistrer",
        "en": "Save settings",
    },
    "settings_save_restart": {
        "it": "Salva e riavvia kiosk",
        "fr": "Enregistrer et redémarrer le kiosk",
        "en": "Save and restart kiosk",
    },
    "settings_env_file": {
        "it": "File configurazione:",
        "fr": "Fichier de configuration :",
        "en": "Configuration file:",
    },
    "settings_active": {"it": "Attivo", "fr": "Actif", "en": "Active"},
    "settings_secret_set": {
        "it": "•••••• (impostata)",
        "fr": "•••••• (définie)",
        "en": "•••••• (set)",
    },
    "settings_secret_empty": {
        "it": "Non impostata",
        "fr": "Non définie",
        "en": "Not set",
    },
    "settings_backup_title": {"it": "Backup", "fr": "Sauvegarde", "en": "Backup"},
    "settings_backup_sub": {
        "it": "Database, coda locale, configurazione e sfondo kiosk",
        "fr": "Base de données, file locale, configuration et fond kiosk",
        "en": "Database, local queue, configuration and kiosk background",
    },
    "settings_backup_hint": {
        "it": "Scarica un archivio ZIP con tutti i dati essenziali.",
        "fr": "Téléchargez une archive ZIP avec toutes les données essentielles.",
        "en": "Download a ZIP archive with all essential data.",
    },
    "settings_backup_btn": {
        "it": "Scarica backup ZIP",
        "fr": "Télécharger la sauvegarde ZIP",
        "en": "Download backup ZIP",
    },
    "settings_after_title": {
        "it": "Dopo le modifiche",
        "fr": "Après les modifications",
        "en": "After changes",
    },
    "section_kiosk": {
        "it": "Kiosk / Timbratrice",
        "fr": "Kiosk / Pointeuse",
        "en": "Kiosk / Clock terminal",
    },
    "section_network_lan": {
        "it": "Rete LAN (Raspberry Pi)",
        "fr": "Réseau LAN (Raspberry Pi)",
        "en": "LAN network (Raspberry Pi)",
    },
    "section_network_app": {
        "it": "Dashboard e sincronizzazione",
        "fr": "Tableau de bord et synchronisation",
        "en": "Dashboard and sync",
    },
    "section_system": {
        "it": "Sistema e sicurezza",
        "fr": "Système et sécurité",
        "en": "System and security",
    },
    # --- Campi impostazioni ---
    "setting_KIOSK_LANG": {
        "it": "Lingua (dashboard + kiosk)",
        "fr": "Langue (tableau de bord + kiosk)",
        "en": "Language (dashboard + kiosk)",
    },
    "hint_KIOSK_LANG": {
        "it": "Italiano, Français o English — pagine web e touchscreen",
        "fr": "Italien, Français ou English — pages web et écran tactile",
        "en": "Italian, French or English — web pages and touchscreen",
    },
    "setting_KIOSK_BACKGROUND": {
        "it": "Sfondo kiosk (path)",
        "fr": "Fond kiosk (chemin)",
        "en": "Kiosk background (path)",
    },
    "setting_DISPLAY_WIDTH": {"it": "Larghezza display", "fr": "Largeur écran", "en": "Display width"},
    "setting_DISPLAY_HEIGHT": {"it": "Altezza display", "fr": "Hauteur écran", "en": "Display height"},
    "setting_KIOSK_CONFIRM_MS": {
        "it": "Durata messaggio conferma (ms)",
        "fr": "Durée message de confirmation (ms)",
        "en": "Confirmation message duration (ms)",
    },
    "setting_NFC_AUTO_TIMBRATURA": {
        "it": "Timbratura automatica NFC",
        "fr": "Pointage NFC automatique",
        "en": "Automatic NFC clock-in",
    },
    "hint_NFC_AUTO_TIMBRATURA": {
        "it": "1° passaggio = entrata, 2° = uscita (senza pulsanti touch)",
        "fr": "1er passage = entrée, 2e = sortie (sans boutons tactiles)",
        "en": "1st tap = in, 2nd = out (no touch buttons)",
    },
    "setting_MIN_SECONDI_TRA_TIMBRATURE": {
        "it": "Secondi minimi tra timbrature",
        "fr": "Secondes min. entre pointages",
        "en": "Min. seconds between clock events",
    },
    "setting_NFC_BACKEND": {"it": "Backend NFC", "fr": "Backend NFC", "en": "NFC backend"},
    "setting_NFC_DEVICE_PATH": {
        "it": "Path dispositivo NFC",
        "fr": "Chemin périphérique NFC",
        "en": "NFC device path",
    },
    "setting_MOCK_NFC": {
        "it": "Modalità mock NFC (test)",
        "fr": "Mode mock NFC (test)",
        "en": "NFC mock mode (test)",
    },
    "setting_MOCK_GPIO": {
        "it": "Modalità mock GPIO (test)",
        "fr": "Mode mock GPIO (test)",
        "en": "GPIO mock mode (test)",
    },
    "setting_NETWORK_MODE": {
        "it": "Configurazione IP",
        "fr": "Configuration IP",
        "en": "IP configuration",
    },
    "hint_NETWORK_MODE": {
        "it": "DHCP: indirizzo dal router. Manuale: IP, maschera e gateway fissi.",
        "fr": "DHCP : adresse du routeur. Manuel : IP, masque et passerelle fixes.",
        "en": "DHCP: address from router. Manual: fixed IP, subnet and gateway.",
    },
    "setting_LAN_IP": {
        "it": "Indirizzo IP (LAN)",
        "fr": "Adresse IP (LAN)",
        "en": "IP address (LAN)",
    },
    "hint_LAN_IP": {
        "it": "Es. 192.168.178.124 — indirizzo nel browser da altri PC",
        "fr": "Ex. 192.168.178.124 — adresse dans le navigateur depuis d'autres PC",
        "en": "E.g. 192.168.178.124 — browser address from other PCs",
    },
    "setting_LAN_SUBNET": {
        "it": "Maschera di sottorete",
        "fr": "Masque de sous-réseau",
        "en": "Subnet mask",
    },
    "setting_LAN_GATEWAY": {
        "it": "Gateway (router)",
        "fr": "Passerelle (routeur)",
        "en": "Gateway (router)",
    },
    "hint_LAN_GATEWAY": {
        "it": "Es. 192.168.178.1",
        "fr": "Ex. 192.168.178.1",
        "en": "E.g. 192.168.178.1",
    },
    "setting_LAN_DNS": {
        "it": "DNS (opzionale)",
        "fr": "DNS (optionnel)",
        "en": "DNS (optional)",
    },
    "hint_LAN_DNS": {
        "it": "Lasciare vuoto per usare il gateway come DNS",
        "fr": "Laisser vide pour utiliser la passerelle comme DNS",
        "en": "Leave empty to use gateway as DNS",
    },
    "setting_DASHBOARD_URL": {
        "it": "URL dashboard (da altri PC)",
        "fr": "URL tableau de bord (depuis d'autres PC)",
        "en": "Dashboard URL (from other PCs)",
    },
    "hint_DASHBOARD_URL": {
        "it": "Aprire questo indirizzo dal browser su PC/tablet in rete locale",
        "fr": "Ouvrir cette adresse dans le navigateur depuis un PC/tablette sur le LAN",
        "en": "Open this address in a browser from PCs/tablets on the LAN",
    },
    "setting_LAN_INTERFACE": {
        "it": "Interfaccia di rete",
        "fr": "Interface réseau",
        "en": "Network interface",
    },
    "setting_SERVER_PORT": {"it": "Porta dashboard", "fr": "Port dashboard", "en": "Dashboard port"},
    "setting_SERVER_URL": {
        "it": "URL API kiosk (locale)",
        "fr": "URL API kiosk (local)",
        "en": "Kiosk API URL (local)",
    },
    "hint_SERVER_URL": {
        "it": "Il kiosk sulla stessa Pi usa 127.0.0.1 — non è l'IP LAN",
        "fr": "Le kiosk sur la même Pi utilise 127.0.0.1 — ce n'est pas l'IP LAN",
        "en": "Kiosk on the same Pi uses 127.0.0.1 — not the LAN IP",
    },
    "setting_SERVER_HOST": {
        "it": "Bind server (tecnico)",
        "fr": "Écoute serveur (technique)",
        "en": "Server bind (technical)",
    },
    "hint_SERVER_HOST": {
        "it": "0.0.0.0 = il server ascolta su tutte le interfacce (corretto per LAN)",
        "fr": "0.0.0.0 = le serveur écoute sur toutes les interfaces (correct pour le LAN)",
        "en": "0.0.0.0 = server listens on all interfaces (correct for LAN)",
    },
    "settings_saved_network": {
        "it": "Impostazioni e configurazione rete salvate.",
        "fr": "Paramètres et configuration réseau enregistrés.",
        "en": "Settings and network configuration saved.",
    },
    "settings_network_warn": {
        "it": "Impostazioni salvate, ma la rete non è stata applicata:",
        "fr": "Paramètres enregistrés, mais le réseau n'a pas été appliqué :",
        "en": "Settings saved, but network was not applied:",
    },
    "network_mode_dhcp": {
        "it": "DHCP (automatico)",
        "fr": "DHCP (automatique)",
        "en": "DHCP (automatic)",
    },
    "network_mode_manual": {
        "it": "IP statico (manuale)",
        "fr": "IP statique (manuel)",
        "en": "Static IP (manual)",
    },
    "setting_API_KEY": {"it": "API Key", "fr": "Clé API", "en": "API Key"},
    "hint_API_KEY": {
        "it": "Opzionale in LAN chiusa; lasciare vuoto per non cambiare",
        "fr": "Optionnel en LAN fermé ; laisser vide pour ne pas modifier",
        "en": "Optional on closed LAN; leave empty to keep current value",
    },
    "setting_SYNC_INTERVAL_SEC": {
        "it": "Intervallo sync anagrafica (sec)",
        "fr": "Intervalle sync annuaire (sec)",
        "en": "Directory sync interval (sec)",
    },
    "setting_HEARTBEAT_INTERVAL_SEC": {
        "it": "Intervallo heartbeat (sec)",
        "fr": "Intervalle heartbeat (sec)",
        "en": "Heartbeat interval (sec)",
    },
    "setting_TIMBRANFC_DATA": {"it": "Cartella dati", "fr": "Dossier données", "en": "Data folder"},
    "setting_ADMIN_EMAIL": {
        "it": "Email amministratore",
        "fr": "E-mail administrateur",
        "en": "Administrator email",
    },
    "setting_ADMIN_PASSWORD": {
        "it": "Password amministratore",
        "fr": "Mot de passe administrateur",
        "en": "Administrator password",
    },
    "hint_ADMIN_PASSWORD": {
        "it": "Lasciare vuoto per non modificare",
        "fr": "Laisser vide pour ne pas modifier",
        "en": "Leave empty to keep current value",
    },
    "setting_SECRET_KEY": {"it": "Secret key sessioni", "fr": "Clé secrète sessions", "en": "Session secret key"},
    "hint_SECRET_KEY": {
        "it": "Lasciare vuoto per non modificare",
        "fr": "Laisser vide pour ne pas modifier",
        "en": "Leave empty to keep current value",
    },
    # --- Web: comune UI ---
    "lbl_search": {"it": "Cerca", "fr": "Rechercher", "en": "Search"},
    "lbl_status": {"it": "Stato", "fr": "Statut", "en": "Status"},
    "lbl_department": {"it": "Reparto", "fr": "Service", "en": "Department"},
    "lbl_month": {"it": "Mese", "fr": "Mois", "en": "Month"},
    "lbl_employee": {"it": "Dipendente", "fr": "Employé", "en": "Employee"},
    "lbl_all": {"it": "Tutti", "fr": "Tous", "en": "All"},
    "lbl_from": {"it": "Da", "fr": "Du", "en": "From"},
    "lbl_to": {"it": "A", "fr": "Au", "en": "To"},
    "lbl_or_period": {"it": "oppure periodo:", "fr": "ou période :", "en": "or period:"},
    "btn_filter": {"it": "Filtra", "fr": "Filtrer", "en": "Filter"},
    "btn_export_csv": {"it": "Export CSV", "fr": "Export CSV", "en": "Export CSV"},
    "btn_export_list": {"it": "Esporta elenco", "fr": "Exporter la liste", "en": "Export list"},
    "btn_manage": {"it": "Gestisci →", "fr": "Gérer →", "en": "Manage →"},
    "btn_save": {"it": "Salva", "fr": "Enregistrer", "en": "Save"},
    "btn_save_changes": {"it": "Salva modifiche", "fr": "Enregistrer", "en": "Save changes"},
    "btn_cancel": {"it": "Annulla", "fr": "Annuler", "en": "Cancel"},
    "col_name": {"it": "Nome", "fr": "Prénom", "en": "First name"},
    "col_surname": {"it": "Cognome", "fr": "Nom", "en": "Last name"},
    "col_badge": {"it": "Badge UID", "fr": "UID badge", "en": "Badge UID"},
    "col_department": {"it": "Reparto", "fr": "Service", "en": "Department"},
    "col_email": {"it": "Email", "fr": "E-mail", "en": "Email"},
    "col_actions": {"it": "Azioni", "fr": "Actions", "en": "Actions"},
    "col_id": {"it": "ID", "fr": "ID", "en": "ID"},
    "col_date": {"it": "Data", "fr": "Date", "en": "Date"},
    "col_time": {"it": "Ora", "fr": "Heure", "en": "Time"},
    "col_terminal": {"it": "Terminale", "fr": "Terminal", "en": "Terminal"},
    "col_received": {"it": "Ricevuto server", "fr": "Reçu serveur", "en": "Received by server"},
    "col_action": {"it": "Azione", "fr": "Action", "en": "Action"},
    "col_days": {"it": "Giorni", "fr": "Jours", "en": "Days"},
    "col_n_shifts": {"it": "N. turni", "fr": "N. postes", "en": "Shifts"},
    "col_total_hours": {"it": "Ore totali", "fr": "Heures totales", "en": "Total hours"},
    "col_total_time": {"it": "Tempo totale", "fr": "Temps total", "en": "Total time"},
    "col_timeline": {"it": "Timeline turno", "fr": "Chronologie poste", "en": "Shift timeline"},
    "status_active": {"it": "Attivo", "fr": "Actif", "en": "Active"},
    "status_inactive": {"it": "Disattivo", "fr": "Inactif", "en": "Inactive"},
    "status_online": {"it": "Online", "fr": "En ligne", "en": "Online"},
    "status_offline": {"it": "Offline", "fr": "Hors ligne", "en": "Offline"},
    "all_departments": {"it": "Tutti i reparti", "fr": "Tous les services", "en": "All departments"},
    "active_only": {"it": "Solo attivi", "fr": "Actifs seulement", "en": "Active only"},
    "inactive_only": {"it": "Solo disattivati", "fr": "Inactifs seulement", "en": "Inactive only"},
    "online_only": {"it": "Solo online", "fr": "En ligne seulement", "en": "Online only"},
    "offline_only": {"it": "Solo offline", "fr": "Hors ligne seulement", "en": "Offline only"},
    "results_label": {"it": "risultati", "fr": "résultats", "en": "results"},
    "period_label": {"it": "Periodo:", "fr": "Période :", "en": "Period:"},
    "breadcrumb_presences": {"it": "Presenze", "fr": "Présences", "en": "Attendance"},
    "back_to_dip": {"it": "← Torna a Dipendenti", "fr": "← Retour aux employés", "en": "← Back to employees"},
    "badge_label": {"it": "badge", "fr": "badge", "en": "badge"},
    "badge_current": {"it": "badge attuale", "fr": "badge actuel", "en": "current badge"},
    # --- Dipendenti ---
    "dip_subtitle": {
        "it": "Aggiungi, modifica, disattiva o riassegna il badge NFC di ogni dipendente.",
        "fr": "Ajoutez, modifiez, désactivez ou réassignez le badge NFC de chaque employé.",
        "en": "Add, edit, deactivate or reassign each employee's NFC badge.",
    },
    "dip_new": {"it": "Nuovo dipendente", "fr": "Nouvel employé", "en": "New employee"},
    "dip_list": {"it": "Elenco dipendenti", "fr": "Liste des employés", "en": "Employee list"},
    "dip_no_employees": {
        "it": "Nessun dipendente registrato",
        "fr": "Aucun employé enregistré",
        "en": "No employees registered",
    },
    "dip_save": {"it": "Salva dipendente", "fr": "Enregistrer l'employé", "en": "Save employee"},
    "dip_search_ph": {
        "it": "Nome, cognome o badge UID…",
        "fr": "Prénom, nom ou UID badge…",
        "en": "First name, surname or badge UID…",
    },
    "btn_edit": {"it": "Modifica", "fr": "Modifier", "en": "Edit"},
    "btn_badge": {"it": "Badge", "fr": "Badge", "en": "Badge"},
    "btn_deactivate": {"it": "Disattiva", "fr": "Désactiver", "en": "Deactivate"},
    "btn_reactivate": {"it": "Riattiva", "fr": "Réactiver", "en": "Reactivate"},
    "btn_delete": {"it": "Elimina", "fr": "Supprimer", "en": "Delete"},
    "dip_delete_confirm": {
        "it": "Eliminare {name}? Se ha timbrature verrà solo disattivato.",
        "fr": "Supprimer {name} ? S'il a des pointages, il sera seulement désactivé.",
        "en": "Delete {name}? If they have clock events, they will only be deactivated.",
    },
    "msg_dip_added": {
        "it": "Dipendente aggiunto correttamente.",
        "fr": "Employé ajouté avec succès.",
        "en": "Employee added successfully.",
    },
    "msg_dip_updated": {
        "it": "Dipendente aggiornato.",
        "fr": "Employé mis à jour.",
        "en": "Employee updated.",
    },
    "msg_badge_updated": {
        "it": "Badge NFC aggiornato.",
        "fr": "Badge NFC mis à jour.",
        "en": "NFC badge updated.",
    },
    "msg_dip_deactivated": {
        "it": "Dipendente disattivato.",
        "fr": "Employé désactivé.",
        "en": "Employee deactivated.",
    },
    "msg_dip_reactivated": {
        "it": "Dipendente riattivato.",
        "fr": "Employé réactivé.",
        "en": "Employee reactivated.",
    },
    "msg_dip_deleted": {
        "it": "Dipendente eliminato.",
        "fr": "Employé supprimé.",
        "en": "Employee deleted.",
    },
    "msg_dip_deactivated_arch": {
        "it": "Non eliminato: ha timbrature in archivio — dipendente disattivato.",
        "fr": "Non supprimé : pointages en archive — employé désactivé.",
        "en": "Not deleted: has archived clock events — employee deactivated.",
    },
    "err_badge_duplicate": {
        "it": "Badge già associato a un altro dipendente.",
        "fr": "Badge déjà associé à un autre employé.",
        "en": "Badge already assigned to another employee.",
    },
    "err_badge_empty": {
        "it": "Registra prima un badge NFC.",
        "fr": "Enregistrez d'abord un badge NFC.",
        "en": "Register an NFC badge first.",
    },
    "err_not_found": {
        "it": "Dipendente non trovato.",
        "fr": "Employé introuvable.",
        "en": "Employee not found.",
    },
    "edit_dip_title": {
        "it": "Modifica dipendente",
        "fr": "Modifier l'employé",
        "en": "Edit employee",
    },
    "edit_dip_hint": {
        "it": "Per cambiare il badge NFC usa",
        "fr": "Pour changer le badge NFC utilisez",
        "en": "To change the NFC badge use",
    },
    "edit_dip_reassign": {
        "it": "Riassegna badge →",
        "fr": "Réassigner le badge →",
        "en": "Reassign badge →",
    },
    "breadcrumb_edit": {"it": "Modifica", "fr": "Modifier", "en": "Edit"},
    "badge_reassign_title": {
        "it": "Riassegna badge NFC",
        "fr": "Réassigner le badge NFC",
        "en": "Reassign NFC badge",
    },
    "breadcrumb_badge": {
        "it": "Riassegna badge",
        "fr": "Réassigner badge",
        "en": "Reassign badge",
    },
    "badge_reassign_info": {
        "it": "Il vecchio badge verrà disattivato non appena il nuovo viene salvato.",
        "fr": "L'ancien badge sera désactivé dès que le nouveau sera enregistré.",
        "en": "The old badge will be deactivated once the new one is saved.",
    },
    "badge_new_label": {"it": "Nuovo badge NFC", "fr": "Nouveau badge NFC", "en": "New NFC badge"},
    "badge_save_new": {
        "it": "Salva nuovo badge",
        "fr": "Enregistrer le nouveau badge",
        "en": "Save new badge",
    },
    "err_badge_read_first": {
        "it": "Leggi prima un badge NFC.",
        "fr": "Lisez d'abord un badge NFC.",
        "en": "Read an NFC badge first.",
    },
    "enroll_badge_label": {"it": "Badge NFC", "fr": "Badge NFC", "en": "NFC badge"},
    "enroll_rescan": {"it": "Rileggi badge", "fr": "Relire le badge", "en": "Rescan badge"},
    "enroll_placeholder": {
        "it": "In attesa lettura badge…",
        "fr": "En attente de lecture…",
        "en": "Waiting for badge scan…",
    },
    "enroll_click_wait": {
        "it": "Clicca «Rileggi badge» e avvicina il badge al lettore NFC del Raspberry Pi.",
        "fr": "Cliquez « Relire le badge » et approchez le badge du lecteur NFC.",
        "en": "Click «Rescan badge» and hold the badge to the NFC reader.",
    },
    "enroll_click_wait_new": {
        "it": "Clicca «Rileggi badge» e avvicina il nuovo badge al lettore NFC del Raspberry Pi.",
        "fr": "Cliquez « Relire le badge » et approchez le nouveau badge du lecteur NFC.",
        "en": "Click «Rescan badge» and hold the new badge to the NFC reader.",
    },
    "enroll_near_reader": {
        "it": "Avvicina il badge al lettore NFC del Raspberry Pi.",
        "fr": "Approchez le badge du lecteur NFC.",
        "en": "Hold the badge to the NFC reader.",
    },
    "enroll_captured": {
        "it": "Badge registrato: {uid}",
        "fr": "Badge enregistré : {uid}",
        "en": "Badge registered: {uid}",
    },
    "enroll_duplicate_js": {
        "it": "Badge già registrato su un altro dipendente — usa un badge diverso.",
        "fr": "Badge déjà enregistré sur un autre employé — utilisez un badge différent.",
        "en": "Badge already registered to another employee — use a different badge.",
    },
    "enroll_expired": {
        "it": "Sessione scaduta — clicca «Rileggi badge».",
        "fr": "Session expirée — cliquez « Relire le badge ».",
        "en": "Session expired — click «Rescan badge».",
    },
    "enroll_conn_error": {
        "it": "Errore di connessione al server.",
        "fr": "Erreur de connexion au serveur.",
        "en": "Server connection error.",
    },
    "enroll_start_error": {
        "it": "Impossibile avviare la registrazione badge.",
        "fr": "Impossible de démarrer l'enregistrement du badge.",
        "en": "Cannot start badge registration.",
    },
    "js_showing_dip": {
        "it": "Mostrando {visible} di {total} dipendenti",
        "fr": "Affichage de {visible} sur {total} employés",
        "en": "Showing {visible} of {total} employees",
    },
    # --- Timbrature ---
    "timbr_subtitle_pre": {
        "it": "Elenco completo delle timbrature registrate. Per ore e turni usa",
        "fr": "Liste complète des pointages. Pour les heures et postes utilisez",
        "en": "Full list of recorded clock events. For hours and shifts use",
    },
    "timbr_subtitle_link": {"it": "Report turni →", "fr": "Rapport postes →", "en": "Shift report →"},
    "msg_timbr_cleared": {
        "it": "Timbrature azzerate: {n} dal server{local}.",
        "fr": "Pointages effacés : {n} du serveur{local}.",
        "en": "Clock events cleared: {n} from server{local}.",
    },
    "msg_timbr_cleared_local": {
        "it": ", {nl} dalla coda locale",
        "fr": ", {nl} de la file locale",
        "en": ", {nl} from local queue",
    },
    "err_confirm_reset": {
        "it": "Conferma non valida — digita esattamente AZZERA.",
        "fr": "Confirmation invalide — tapez exactement AZZERA.",
        "en": "Invalid confirmation — type AZZERA exactly.",
    },
    "timbr_no_data": {
        "it": "Nessuna timbratura nel periodo selezionato",
        "fr": "Aucun pointage pour la période sélectionnée",
        "en": "No clock events in the selected period",
    },
    "timbr_count": {"it": "timbrature", "fr": "pointages", "en": "clock events"},
    "timbr_filter_employee": {
        "it": "filtro dipendente attivo",
        "fr": "filtre employé actif",
        "en": "employee filter active",
    },
    "timbr_clear_title": {"it": "Azzera timbrature", "fr": "Effacer les pointages", "en": "Clear clock events"},
    "timbr_clear_desc": {
        "it": "Elimina tutte le timbrature di tutti i dipendenti ({n} nel database). I dipendenti e i badge restano invariati. Operazione irreversibile.",
        "fr": "Supprime tous les pointages de tous les employés ({n} en base). Les employés et badges restent inchangés. Irréversible.",
        "en": "Deletes all clock events for all employees ({n} in database). Employees and badges unchanged. Irreversible.",
    },
    "timbr_clear_confirm_lbl": {
        "it": "Digita AZZERA per confermare",
        "fr": "Tapez AZZERA pour confirmer",
        "en": "Type AZZERA to confirm",
    },
    "timbr_clear_btn": {
        "it": "Azzera tutte le timbrature",
        "fr": "Effacer tous les pointages",
        "en": "Clear all clock events",
    },
    "timbr_clear_confirm_js": {
        "it": "Eliminare TUTTE le timbrature?",
        "fr": "Supprimer TOUS les pointages ?",
        "en": "Delete ALL clock events?",
    },
    "js_stamps_dept": {
        "it": "{n} timbrature (filtro reparto: {dept})",
        "fr": "{n} pointages (filtre service : {dept})",
        "en": "{n} clock events (department filter: {dept})",
    },
    "js_dept_all": {"it": "tutti", "fr": "tous", "en": "all"},
    # --- Report ---
    "report_subtitle_pre": {
        "it": "Turni calcolati dalle timbrature (entrata/uscita). Elenco eventi grezzi in",
        "fr": "Postes calculés à partir des pointages. Événements bruts dans",
        "en": "Shifts calculated from clock events. Raw events in",
    },
    "report_subtitle_link": {"it": "Timbrature →", "fr": "Pointages →", "en": "Clock events →"},
    "report_summary": {"it": "Riepilogo periodo", "fr": "Résumé période", "en": "Period summary"},
    "report_detail": {"it": "Dettaglio turni", "fr": "Détail des postes", "en": "Shift details"},
    "report_no_shifts": {
        "it": "Nessun turno nel periodo selezionato",
        "fr": "Aucun poste pour la période sélectionnée",
        "en": "No shifts in the selected period",
    },
    "report_no_completed": {
        "it": "Nessun turno completato nel periodo",
        "fr": "Aucun poste terminé sur la période",
        "en": "No completed shifts in the period",
    },
    "shift_in_progress": {"it": "in corso", "fr": "en cours", "en": "in progress"},
    # --- Dispositivi ---
    "dev_title": {"it": "Flotta terminali", "fr": "Flotte terminaux", "en": "Terminal fleet"},
    "dev_subtitle": {
        "it": "Stato in tempo reale dei terminali NFC collegati e azioni remote.",
        "fr": "État en temps réel des terminaux NFC et actions à distance.",
        "en": "Real-time status of connected NFC terminals and remote actions.",
    },
    "dev_online_kpi": {"it": "Terminali online", "fr": "Terminaux en ligne", "en": "Terminals online"},
    "dev_offline_kpi": {"it": "Terminali offline", "fr": "Terminaux hors ligne", "en": "Terminals offline"},
    "dev_total_kpi": {"it": "Totale registrati", "fr": "Total enregistrés", "en": "Total registered"},
    "dev_search_ph": {
        "it": "Nome o UUID terminale…",
        "fr": "Nom ou UUID terminal…",
        "en": "Terminal name or UUID…",
    },
    "dev_no_devices": {
        "it": "Nessun terminale registrato",
        "fr": "Aucun terminal enregistré",
        "en": "No terminal registered",
    },
    "dev_no_devices_hint": {
        "it": "I terminali appariranno qui non appena effettuano il primo heartbeat verso il server.",
        "fr": "Les terminaux apparaîtront ici après leur premier heartbeat.",
        "en": "Terminals will appear here after their first heartbeat to the server.",
    },
    "dev_sw_version": {"it": "Versione SW", "fr": "Version SW", "en": "SW version"},
    "dev_last_hb": {"it": "Ultimo heartbeat", "fr": "Dernier heartbeat", "en": "Last heartbeat"},
    "dev_restart_kiosk": {"it": "Restart kiosk", "fr": "Redémarrer kiosk", "en": "Restart kiosk"},
    # --- Home extra ---
    "home_recent_sub": {
        "it": "Le 10 timbrature più recenti ricevute dal server",
        "fr": "Les 10 derniers pointages reçus par le serveur",
        "en": "The 10 most recent clock events received by the server",
    },
    "col_received_at": {"it": "Ricevuto il", "fr": "Reçu le", "en": "Received at"},
    "home_dev_title": {"it": "Stato dispositivi", "fr": "État des terminaux", "en": "Device status"},
    "home_dev_sub": {
        "it": "{n} terminali registrati in flotta",
        "fr": "{n} terminaux enregistrés dans la flotte",
        "en": "{n} terminals registered in fleet",
    },
    "home_dev_hint": {
        "it": "Stato heartbeat e riavvio kiosk dalla pagina Terminale (menu laterale).",
        "fr": "État heartbeat et redémarrage kiosk depuis la page Terminal (menu latéral).",
        "en": "Heartbeat status and kiosk restart from the Terminals page (sidebar menu).",
    },
    "home_dev_hint_pre": {
        "it": "Vai alla pagina",
        "fr": "Allez à la page",
        "en": "Go to the",
    },
    "home_dev_hint_post": {
        "it": "per il dettaglio di ogni terminale e le azioni remote.",
        "fr": "pour le détail de chaque terminal et les actions à distance.",
        "en": "page for each terminal detail and remote actions.",
    },
    # --- Kiosk ---
    "badge_not_found": {
        "it": "Badge non riconosciuto",
        "fr": "Badge non reconnu",
        "en": "Badge not recognized",
    },
    "wait_before_stamp": {
        "it": "Attendere prima di timbrare di nuovo",
        "fr": "Veuillez patienter avant de pointer à nouveau",
        "en": "Please wait before clocking in again",
    },
    "invalid_action": {
        "it": "Azione non valida",
        "fr": "Action non valide",
        "en": "Invalid action",
    },
    "invalid_transition": {
        "it": "Transizione non valida",
        "fr": "Transition non valide",
        "en": "Invalid transition",
    },
    "no_action_available": {
        "it": "Nessuna azione disponibile",
        "fr": "Aucune action disponible",
        "en": "No action available",
    },
    "state_unavailable": {
        "it": "Timbratura non disponibile",
        "fr": "Pointage non disponible",
        "en": "Clock-in not available",
    },
    "error_generic": {"it": "Errore", "fr": "Erreur", "en": "Error"},
    "cancel": {"it": "Annulla", "fr": "Annuler", "en": "Cancel"},
    "state_label": {"it": "Stato", "fr": "Statut", "en": "Status"},
    "enrollment_ok": {
        "it": "Badge registrato",
        "fr": "Badge enregistré",
        "en": "Badge registered",
    },
    "enrollment_duplicate": {
        "it": "Badge già in uso",
        "fr": "Badge déjà utilisé",
        "en": "Badge already in use",
    },
    "action_IT": {"it": "Inizio Turno", "fr": "Début de poste", "en": "Shift start"},
    "action_IP": {"it": "Inizio Pausa", "fr": "Début de pause", "en": "Break start"},
    "action_FP": {"it": "Fine Pausa", "fr": "Fin de pause", "en": "Break end"},
    "action_FT": {"it": "Fine Turno", "fr": "Fin de poste", "en": "Shift end"},
    "stato_FUORI_TURNO": {"it": "Fuori turno", "fr": "Hors poste", "en": "Off shift"},
    "stato_IN_TURNO": {"it": "In turno", "fr": "En poste", "en": "On shift"},
    "stato_IN_PAUSA": {"it": "In pausa", "fr": "En pause", "en": "On break"},
}

_LOCALE_MAP = {
    "it": "it_IT.UTF-8",
    "fr": "fr_FR.UTF-8",
    "en": "en_GB.UTF-8",
}

_LANG_LABELS = {
    "it": "Italiano",
    "fr": "Français",
    "en": "English",
}


def normalize_lang(lang: str | None) -> Lang:
    if not lang:
        return _DEFAULT_LANG
    code = lang.strip().lower()[:2]
    return code if code in _SUPPORTED else _DEFAULT_LANG


def current_lang() -> Lang:
    """Lingua da .env (dashboard) o variabile d'ambiente (kiosk)."""
    try:
        from server.app.services.settings_env import read_settings

        return normalize_lang(read_settings().get("KIOSK_LANG"))
    except Exception:
        return normalize_lang(os.environ.get("KIOSK_LANG", _DEFAULT_LANG))


def t(key: str, lang: Lang | None = None) -> str:
    code = normalize_lang(lang) if lang else current_lang()
    bucket = _STRINGS.get(key, {})
    return bucket.get(code) or bucket.get(_DEFAULT_LANG) or key


def field_label(key: str, fallback: str = "", lang: Lang | None = None) -> str:
    return t(f"setting_{key}", lang) if f"setting_{key}" in _STRINGS else (fallback or key)


def field_hint(key: str, fallback: str = "", lang: Lang | None = None) -> str:
    hint_key = f"hint_{key}"
    if hint_key in _STRINGS:
        return t(hint_key, lang)
    return fallback


def section_label(section_id: str, fallback: str = "", lang: Lang | None = None) -> str:
    return t(f"section_{section_id}", lang) if f"section_{section_id}" in _STRINGS else fallback


def action_label(azione: str, lang: Lang | None = None) -> str:
    return t(f"action_{azione}", lang)


def stato_label(stato: str, lang: Lang | None = None) -> str:
    return t(f"stato_{stato}", lang)


def locale_name(lang: Lang | None = None) -> str:
    code = normalize_lang(lang) if lang else current_lang()
    return _LOCALE_MAP.get(code, "it_IT.UTF-8")


def lang_label(code: str) -> str:
    return _LANG_LABELS.get(normalize_lang(code), code)


def enrollment_js_strings(lang: Lang | None = None) -> dict[str, str]:
    """Stringhe per enrollment.js (window.TIMBRANFC_I18N)."""
    code = normalize_lang(lang) if lang else current_lang()
    keys = [
        "enroll_click_wait",
        "enroll_near_reader",
        "enroll_captured",
        "enroll_duplicate_js",
        "enroll_expired",
        "enroll_conn_error",
        "enroll_start_error",
    ]
    return {k: t(k, code) for k in keys}
