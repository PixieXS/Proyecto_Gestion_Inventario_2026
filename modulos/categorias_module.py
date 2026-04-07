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

        # ── Formulario ────────────────────────────────────────────────────────
        frm_f = ttk.LabelFrame(self.win, text="Datos", padding=10)
        frm_f.pack(fill=tk.X, padx=16, pady=(0, 6))

        ttk.Label(frm_f, text="Nombre:").grid(     row=0, column=0, sticky='e', padx=6, pady=4)
        self.e_nombre = ttk.Entry(frm_f, width=30)
        self.e_nombre.grid(row=0, column=1, pady=4, sticky='w')

        ttk.Label(frm_f, text="Descripción:").grid(row=1, column=0, sticky='e', padx=6, pady=4)
        self.e_desc = ttk.Entry(frm_f, width=30)
        self.e_desc.grid(row=1, column=1, pady=4, sticky='w')

        # ── Botones ───────────────────────────────────────────────────────────
        frm_b = ttk.Frame(self.win); frm_b.pack(pady=8)

        ttk.Button(frm_b, text="➕ Crear",
                   command=self._crear,
                   style='Create.TButton').pack(side=tk.LEFT, padx=4)
        ttk.Button(frm_b, text="✏️ Actualizar",
                   command=self._actualizar,
                   style='Update.TButton').pack(side=tk.LEFT, padx=4)
        ttk.Button(frm_b, text="🗑️ Eliminar",
                   command=self._eliminar,
                   style='Delete.TButton').pack(side=tk.LEFT, padx=4)
        ttk.Button(frm_b, text="🔄 Limpiar",
                   command=self._limpiar,
                   style='Neutral.TButton').pack(side=tk.LEFT, padx=4)

    def _cargar(self):
        for r in self.tree.get_children(): self.tree.delete(r)
        for c in self.db.obtener_categorias():
            n_prod = self.db.contar_productos_activos_por_categoria(c['nombre'])
            tag = 'con_productos' if n_prod and n_prod > 0 else 'sin_productos'
            self.tree.insert('', tk.END, tags=(tag,), values=(
                c['id'], c['nombre'], c.get('descripcion', '') or '', n_prod))

    def _seleccionar(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])['values']
        self._id_sel = vals[0]
        self.e_nombre.delete(0, tk.END); self.e_nombre.insert(0, vals[1])
        self.e_desc.delete(0, tk.END);   self.e_desc.insert(0, vals[2] or '')

    def _crear(self):
        nombre = self.e_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("⚠️", "El nombre es requerido.", parent=self.win); return
        ok, msg = self.db.crear_categoria(nombre, self.e_desc.get().strip())
        messagebox.showinfo("✅", msg, parent=self.win) if ok \
            else messagebox.showerror("❌", msg, parent=self.win)
        if ok: self._limpiar(); self._cargar()

    def _actualizar(self):
        if not self._id_sel:
            messagebox.showwarning("⚠️", "Seleccione una categoría de la tabla.", parent=self.win); return
        nombre = self.e_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("⚠️", "El nombre es requerido.", parent=self.win); return
        ok, msg = self.db.actualizar_categoria(self._id_sel, nombre, self.e_desc.get().strip())
        messagebox.showinfo("✅", msg, parent=self.win) if ok \
            else messagebox.showerror("❌", msg, parent=self.win)
        if ok: self._limpiar(); self._cargar()

    def _eliminar(self):
        if not self._id_sel:
            messagebox.showwarning("⚠️", "Seleccione una categoría.", parent=self.win); return
        nombre = self.e_nombre.get().strip()

        # Primera confirmación normal
        if not messagebox.askyesno("🗑️ Eliminar categoría",
                                   f"¿Eliminar la categoría '{nombre}'?\n\n"
                                   f"Esta acción es permanente e irreversible.\n"
                                   f"Solo es posible si ningún producto la usa.",
                                   parent=self.win):
            return

        # Segunda confirmación — contraseña
        autorizado = confirmar_con_password(
            self.win, self.db, self.usuario['id'],
            "🔒 Confirmar eliminación",
            f"Para eliminar '{nombre}' ingrese\nsu contraseña de acceso al sistema.")

        if not autorizado:
            return

        ok, msg = self.db.eliminar_categoria(self._id_sel)
        if ok:
            self.db.registrar_log(
                self.usuario['id'], self.usuario['username'],
                'Eliminar categoría', f"Categoría: {nombre}")
            messagebox.showinfo("✅", msg, parent=self.win)
            self._limpiar(); self._cargar()
        else:
            messagebox.showerror("❌ No se puede eliminar", msg, parent=self.win)

    def _limpiar(self):
        self._id_sel = None
        self.e_nombre.delete(0, tk.END)
        self.e_desc.delete(0, tk.END)
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
