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

     # Agregando Barra De Filtro
        frm_f = ttk.Frame(self.win)
        frm_f.pack(fill=tk.X, padx=12, pady=(0, 6))
        ttk.Label(frm_f, text="Buscar usuario:").pack(side=tk.LEFT, padx=(0, 6))
        self.e_filtro = ttk.Entry(frm_f, width=20)
        self.e_filtro.pack(side=tk.LEFT, padx=(0, 10))
        self.e_filtro.bind('<KeyRelease>', self._filtrar)
        ttk.Button(frm_f, text="🔄 Recargar", command=self._cargar).pack(side=tk.LEFT, padx=4)
