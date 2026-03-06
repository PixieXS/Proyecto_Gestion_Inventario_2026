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

        # Agregando Tabla De Movimiento De Productos Por Usuario
        frm = ttk.Frame(self.win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        sb_y = ttk.Scrollbar(frm); sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x = ttk.Scrollbar(frm, orient=tk.HORIZONTAL); sb_x.pack(side=tk.BOTTOM, fill=tk.X)

        cols = ('ID', 'Usuario', 'Acción', 'Detalle', 'Producto Afectado', 'Fecha')
        self.tree = ttk.Treeview(frm, columns=cols, show='headings',
                                  yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.config(command=self.tree.yview)
        sb_x.config(command=self.tree.xview)

        anchos = {'ID': 45, 'Usuario': 110, 'Acción': 180,
                  'Detalle': 200, 'Producto Afectado': 160, 'Fecha': 150}
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=anchos[c],
                              anchor=tk.CENTER if c == 'ID' else tk.W)

        # Agregando Color A Cada Accion Del Modulo
        self.tree.tag_configure('eliminar',   background='#FEE2E2', foreground='#991B1B')
        self.tree.tag_configure('crear',      background='#D1FAE5', foreground='#065F46')
        self.tree.tag_configure('exportar',   background='#EDE9FE', foreground='#5B21B6')
        self.tree.tag_configure('movimiento', background='#DBEAFE', foreground='#1E3A8A')
        self.tree.tag_configure('login',      background='#FEF9C3', foreground='#854D0E')
        self.tree.tag_configure('default',    background='#F8FAFC')

        self.tree.pack(fill=tk.BOTH, expand=True)

        self._todos = []

    def _cargar(self):
        self._todos = self.db.obtener_log(500)
        self._renderizar(self._todos)

    def _filtrar(self, event=None):
        t = self.e_filtro.get().strip().lower()
        if t:
            filtrado = [r for r in self._todos
                        if t in str(r.get('username', '')).lower()
                        or t in str(r.get('accion', '')).lower()]
        else:
            filtrado = self._todos
        self._renderizar(filtrado)

    def _renderizar(self, registros):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in registros:
            accion = str(r.get('accion', '')).lower()
            if 'eliminar' in accion or 'delete' in accion:
                tag = 'eliminar'
            elif 'crear' in accion or 'nuevo' in accion:
                tag = 'crear'
            elif 'exportar' in accion or 'backup' in accion:
                tag = 'exportar'
            elif 'movimiento' in accion or 'entrada' in accion or 'salida' in accion:
                tag = 'movimiento'
            elif 'login' in accion or 'sesión' in accion or 'password' in accion:
                tag = 'login'
            else:
                tag = 'default'

            self.tree.insert('', tk.END, tags=(tag,), values=(
                r['id'],
                r.get('username', 'Sistema'),
                r.get('accion', ''),
                r.get('detalle', '') or '',
                r.get('producto_afectado', '') or '',
                str(r['fecha'])[:19] if r.get('fecha') else '',
            ))
