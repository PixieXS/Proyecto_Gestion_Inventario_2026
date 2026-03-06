import tkinter as tk
from tkinter import ttk


class LogWindow:
    """Ventana para ver el historial/auditoría del sistema."""

    def __init__(self, master, db):
        self.db = db

        self.win = tk.Toplevel(master)
        self.win.title("🧾 Historial de Actividad del Sistema")
        self.win.geometry("980x520")
        self.win.configure(bg='#F1F5F9')
        self.win.grab_set()

        self._build()
        self._cargar()

    def _build(self):
        ttk.Label(self.win, text="🧾 Auditoría — Registro de Actividad",
                  font=('Segoe UI', 13, 'bold'), background='#F1F5F9',
                  foreground='#2563EB').pack(pady=(12, 4), padx=14)
        ttk.Label(self.win,
                  text="Muestra las últimas 500 acciones registradas en el sistema.",
                  font=('Segoe UI', 9), background='#F1F5F9',
                  foreground='#64748B').pack(padx=14, pady=(0, 8))