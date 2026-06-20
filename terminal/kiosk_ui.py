"""Kiosk UI 480×320 — 4 pulsanti azione, offline-first."""

import locale
import logging
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import terminal.config as config
from terminal import timbratura as timb_logic
from terminal.stati import AZIONI_LABEL

log = logging.getLogger("kiosk_ui")

W = config.DISPLAY_WIDTH
H = config.DISPLAY_HEIGHT
BTN_W, BTN_H = 140, 60
CONFIRM_MS = 2500

COLOR_BG = "#000000"
COLOR_OK = "#0d7377"
COLOR_ERR = "#c62828"
COLOR_BTN = "#2d4059"
COLOR_BTN_ACT = "#4fc3f7"
COLOR_ACCENT = "#e85d04"


class KioskUI:
    def __init__(self, on_badge_callback=None):
        self.root = tk.Tk()
        self.root.title("TimbraNFC")
        self.root.geometry(f"{W}x{H}+0+0")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg=COLOR_BG)
        self.root.bind("<Escape>", lambda e: None)

        self._badge_corrente: str | None = None
        self._btn_refs: dict[str, tk.Button] = {}
        self._bg_photo = None
        self._build_standby()
        self._aggiorna_ora()

    def _clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def _carica_sfondo(self) -> tk.PhotoImage | None:
        path = Path(config.KIOSK_BACKGROUND)
        if not path.is_file():
            log.warning("Sfondo kiosk non trovato: %s", path)
            return None
        try:
            from PIL import Image, ImageTk

            src = Image.open(path).convert("RGBA")
            bbox = src.getbbox()
            if bbox:
                src = src.crop(bbox)

            # Sfondo nero + logo centrato, adattato allo schermo (contain)
            iw, ih = src.size
            scale = min(W / iw, H / ih)
            nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
            logo = src.resize((nw, nh), Image.Resampling.LANCZOS)

            canvas = Image.new("RGB", (W, H), COLOR_BG)
            paste_x = (W - nw) // 2
            paste_y = (H - nh) // 2
            canvas.paste(logo, (paste_x, paste_y), logo.split()[3])

            self._bg_photo = ImageTk.PhotoImage(canvas)
            return self._bg_photo
        except Exception as exc:
            log.warning("Impossibile caricare sfondo kiosk: %s", exc)
            return None

    def _applica_sfondo(self):
        photo = self._carica_sfondo()
        if photo is None:
            return
        tk.Label(self.root, image=photo, bd=0, bg=COLOR_BG).place(x=0, y=0, width=W, height=H)

    def _build_standby(self):
        self._clear()
        self._badge_corrente = None
        self._applica_sfondo()

        # Orario nel margine sinistro (logo centrato lascia bande nere ai lati)
        self.lbl_ora = tk.Label(
            self.root, text="00:00", font=("Helvetica", 22, "bold"), fg="white", bg=COLOR_BG
        )
        self.lbl_ora.place(x=10, y=8, anchor="nw")

        self.lbl_data = tk.Label(
            self.root, text="", font=("Helvetica", 10), fg="#bbbbbb", bg=COLOR_BG
        )
        self.lbl_data.place(x=10, y=36, anchor="nw")

        tk.Label(
            self.root,
            text="Avvicina il badge",
            font=("Helvetica", 15, "bold"),
            fg=COLOR_ACCENT,
            bg=COLOR_BG,
        ).place(relx=0.5, rely=1.0, y=-28, anchor="s")

        tk.Label(
            self.root,
            text="Timbratura presenze",
            font=("Helvetica", 8),
            fg="#777777",
            bg=COLOR_BG,
        ).place(relx=0.5, rely=1.0, y=-8, anchor="s")

    def _build_azione(self, info: dict):
        self._clear()
        self._badge_corrente = info["badge_uid"]
        nome = f"{info['nome']} {info['cognome']}"

        tk.Label(self.root, text=nome, font=("Helvetica", 16, "bold"), fg="white", bg=COLOR_BG).place(
            relx=0.5, rely=0.08, anchor="center"
        )
        tk.Label(self.root, text=f"Stato: {info['stato']}", font=("Helvetica", 12), fg="#aaa", bg=COLOR_BG).place(
            relx=0.5, rely=0.18, anchor="center"
        )

        azioni = info.get("azioni_valide", [])
        positions = [(0.25, 0.45), (0.75, 0.45), (0.25, 0.78), (0.75, 0.78)]
        self._btn_refs = {}

        for i, az in enumerate(azioni[:4]):
            px, py = positions[i]
            btn = tk.Button(
                self.root,
                text=AZIONI_LABEL[az],
                font=("Helvetica", 14, "bold"),
                width=12,
                height=2,
                bg=COLOR_BTN,
                fg="white",
                activebackground=COLOR_BTN_ACT,
                command=lambda a=az: self._on_azione(a),
            )
            btn.place(relx=px, rely=py, anchor="center", width=BTN_W, height=BTN_H)
            self._btn_refs[az] = btn

        tk.Button(
            self.root, text="Annulla", font=("Helvetica", 11), bg="#444", fg="#ccc",
            command=self._build_standby,
        ).place(relx=0.5, rely=0.95, anchor="center")

    def _on_azione(self, azione: str):
        for btn in self._btn_refs.values():
            btn.configure(state=tk.DISABLED)

        result = timb_logic.registra_timbratura(self._badge_corrente, azione)
        self._mostra_conferma(result)

    def _mostra_conferma(self, result: dict):
        self._clear()
        ok = result.get("ok", False)
        bg = COLOR_OK if ok else COLOR_ERR

        if ok:
            testo = f"✓ {result['nome']}\n{result['label']}\n{result['ora']}"
        else:
            testo = f"✗ {result.get('msg', 'Errore')}"

        frame = tk.Frame(self.root, bg=bg, padx=20, pady=15)
        tk.Label(frame, text=testo, font=("Helvetica", 16, "bold"), fg="white", bg=bg, justify="center").pack()
        frame.place(relx=0.5, rely=0.5, anchor="center")
        self.root.after(CONFIRM_MS, self._build_standby)

    def on_badge(self, badge_uid: str):
        self.root.after(0, lambda: self._handle_badge(badge_uid))

    def mostra_enrollment_msg(self, titolo: str, uid: str, *, ok: bool = True):
        self.root.after(0, lambda: self._mostra_enrollment(titolo, uid, ok))

    def _mostra_enrollment(self, titolo: str, uid: str, ok: bool):
        self._clear()
        bg = COLOR_OK if ok else COLOR_ERR
        testo = f"{titolo}\n{uid[:16]}{'…' if len(uid) > 16 else ''}"
        frame = tk.Frame(self.root, bg=bg, padx=20, pady=15)
        tk.Label(frame, text=testo, font=("Helvetica", 14, "bold"), fg="white", bg=bg, justify="center").pack()
        frame.place(relx=0.5, rely=0.5, anchor="center")
        self.root.after(2000, self._build_standby)

    def _handle_badge(self, badge_uid: str):
        info = timb_logic.processa_badge(badge_uid)
        if not info.get("ok"):
            self._mostra_conferma(info)
            return
        if not info.get("azioni_valide"):
            self._mostra_conferma({"ok": False, "msg": "Nessuna azione disponibile"})
            return
        if len(info["azioni_valide"]) == 1:
            result = timb_logic.registra_timbratura(badge_uid, info["azioni_valide"][0])
            self._mostra_conferma(result)
        else:
            self._build_azione(info)

    def _aggiorna_ora(self):
        now = datetime.now()
        if hasattr(self, "lbl_ora") and self.lbl_ora.winfo_exists():
            self.lbl_ora.config(text=now.strftime("%H:%M"))
        if hasattr(self, "lbl_data") and self.lbl_data.winfo_exists():
            try:
                locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")
            except locale.Error:
                pass
            self.lbl_data.config(text=now.strftime("%a %d/%m/%Y"))
        self.root.after(1000, self._aggiorna_ora)

    def run(self):
        self.root.mainloop()
