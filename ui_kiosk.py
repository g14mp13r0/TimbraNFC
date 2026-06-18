import locale
import tkinter as tk
from datetime import datetime

import requests

import config

API = config.API_URL
POLL_MS = 500
CONFIRM_MS = 3000


class TimbratriceUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Timbratrice")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#1a1a2e")
        self.root.bind("<Escape>", lambda e: None)

        self._last_ts = 0
        self._build()
        self._aggiorna_ora()
        self._poll_eventi()

    def _build(self):
        self.lbl_ora = tk.Label(
            self.root, font=("Helvetica", 72, "bold"), fg="white", bg="#1a1a2e"
        )
        self.lbl_ora.place(relx=0.5, rely=0.25, anchor="center")

        self.lbl_data = tk.Label(
            self.root, font=("Helvetica", 24), fg="#aaaaaa", bg="#1a1a2e"
        )
        self.lbl_data.place(relx=0.5, rely=0.4, anchor="center")

        self.lbl_status = tk.Label(
            self.root,
            text="Avvicina il badge",
            font=("Helvetica", 32),
            fg="#4fc3f7",
            bg="#1a1a2e",
        )
        self.lbl_status.place(relx=0.5, rely=0.65, anchor="center")

        self.frame_confirm = tk.Frame(self.root, bg="#0d7377", padx=30, pady=20)
        self.lbl_confirm = tk.Label(
            self.frame_confirm, font=("Helvetica", 28, "bold"), fg="white", bg="#0d7377"
        )
        self.lbl_confirm.pack()

        tk.Label(
            self.root,
            text="Timbratrice Presenze",
            font=("Helvetica", 14),
            fg="#555577",
            bg="#1a1a2e",
        ).place(relx=0.5, rely=0.95, anchor="center")

    def mostra_conferma(self, nome, tipo, ora, ok=True, msg=""):
        color = "#0d7377" if ok else "#c62828"
        if ok:
            testo = f"✓  {nome}\n{tipo.upper()} — {ora}"
        else:
            testo = f"✗  {msg or nome}"

        self.frame_confirm.configure(bg=color)
        self.lbl_confirm.configure(text=testo, bg=color)
        self.frame_confirm.place(relx=0.5, rely=0.65, anchor="center")
        self.lbl_status.place_forget()
        self.root.after(CONFIRM_MS, self._nascondi_conferma)

    def _nascondi_conferma(self):
        self.frame_confirm.place_forget()
        self.lbl_status.place(relx=0.5, rely=0.65, anchor="center")

    def _aggiorna_ora(self):
        now = datetime.now()
        self.lbl_ora.config(text=now.strftime("%H:%M"))
        try:
            locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")
        except locale.Error:
            pass
        self.lbl_data.config(text=now.strftime("%A %d %B %Y").capitalize())
        self.root.after(1000, self._aggiorna_ora)

    def _poll_eventi(self):
        try:
            r = requests.get(f"{API}/api/last-event", timeout=2)
            if r.ok:
                data = r.json()
                ts = data.get("ts", 0)
                if ts and ts != self._last_ts:
                    self._last_ts = ts
                    self.mostra_conferma(
                        data.get("nome", ""),
                        data.get("tipo", ""),
                        data.get("ora", ""),
                        ok=data.get("ok", False),
                        msg=data.get("msg", ""),
                    )
        except requests.RequestException:
            pass
        self.root.after(POLL_MS, self._poll_eventi)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    TimbratriceUI().run()
