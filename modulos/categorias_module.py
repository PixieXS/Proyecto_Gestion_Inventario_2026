import tkinter as tk
from tkinter import ttk, messagebox
from gui.ui_helpers import bloquear_columnas, configurar_ventana, pedir_confirmacion_password


def confirmar_con_password(master, db, id_usuario, titulo, mensaje):
    return pedir_confirmacion_password(
        master, db, id_usuario, titulo, mensaje,
        geometry='360x220',
        prompt_text='Ingrese su contraseña:')


class CategoriasWindow:
    """
    Gestión de categorías:
      - Crear nueva
      - Actualizar nombre/descripción
      - Eliminar (solo si no tiene productos activos) con confirmación de contraseña
    """

    def __init__(self, master, db, usuario):
        self.db      = db
        self.usuario = usuario
        self._id_sel = None

        self.win = tk.Toplevel(master)
        self.win.title("🏷️ Gestionar Categorías")
        self.win.configure(bg='#F1F5F9')
        self.win.grab_set()
        configurar_ventana(self.win, width=760, height=620, min_width=640, min_height=540)
        self._build()
        self._cargar()

    def _build(self):
        ttk.Label(self.win, text="🏷️ Gestionar Categorías",
                  style='Header.TLabel').pack(pady=(14, 2), padx=16, anchor='w')
        ttk.Label(self.win,
                  text="Estas categorías aparecen en el formulario de productos.",
                  foreground='#64748B').pack(padx=16, anchor='w')

        # ── Tabla ─────────────────────────────────────────────────────────────
        frm_t = ttk.Frame(self.win)
        frm_t.pack(fill=tk.BOTH, expand=True, padx=16, pady=(10, 4))

        sb = ttk.Scrollbar(frm_t); sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree = ttk.Treeview(
            frm_t, columns=('ID', 'Nombre', 'Descripción', 'Productos'),
            show='headings', yscrollcommand=sb.set, height=10)
        sb.config(command=self.tree.yview)
        self.tree.heading('ID',          text='ID');          self.tree.column('ID',          width=40, anchor='center')
        self.tree.heading('Nombre',      text='Nombre');      self.tree.column('Nombre',      width=160)
        self.tree.heading('Descripción', text='Descripción'); self.tree.column('Descripción', width=210)
        self.tree.heading('Productos',   text='Productos');   self.tree.column('Productos',   width=80, anchor='center')
        self.tree.tag_configure('con_productos', background='#EFF6FF')
        self.tree.tag_configure('sin_productos', background='#F8FAFC')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(self.tree)
        self.tree.bind('<<TreeviewSelect>>', self._seleccionar)

     