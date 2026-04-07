from gui.estilos import ventana_fullscreen
import tkinter as tk
from tkinter import ttk, messagebox
from gui.ui_helpers import bloquear_columnas, configurar_ventana


class SuppliersWindow:
    """
    Gestión de proveedores.
    - Crear / Actualizar proveedor
    - Inhabilitar (solo si no tiene productos activos asociados)
    - Habilitar    (reactiva un proveedor inhabilitado)
    El botón Eliminar fue reemplazado por Inhabilitar/Habilitar.
    """

    def __init__(self, master, db, usuario, C=None):
        self.db        = db
        self.usuario   = usuario
        self.seleccionado = None
        self.can_edit  = db.tiene_permiso(usuario, 'gestionar_proveedores')
        self._C_ext    = C  # tema externo si se pasa

        self.win = ventana_fullscreen(master, "🏭 Gestión de Proveedores",
                                       C or self._C())
        self._build()
        self._cargar()

    def _C(self):
        """Colores mínimos para widgets que no usan ttk."""
        return {'bg': '#F1F5F9', 'text': '#1E293B',
                'primary': '#2563EB', 'danger': '#EF4444',
                'header_bg': '#1E3A5F', 'muted': '#64748B'}

    def _build(self):
        C = self._C_ext or self._C()

        # Encabezado
        hdr = tk.Frame(self.win, bg=C['header_bg'], height=50)
        hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr, text="🏭  Gestión de Proveedores",
                 font=("Segoe UI", 13, "bold"),
                 bg=C['header_bg'], fg='white').pack(side=tk.LEFT, padx=16)
        body = tk.Frame(self.win, bg=C['bg'])
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        contenedor = tk.Frame(body, bg=body.cget('bg'))
        contenedor.pack(fill=tk.BOTH, expand=True)

        # ── Lista ──────────────────────────────────────────────────────────────
        frm_l = ttk.LabelFrame(contenedor, text="Proveedores", padding=8)
        frm_l.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        # Buscador en tiempo real
        frm_search = ttk.Frame(frm_l)
        frm_search.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(frm_search, text="🔍 Buscar:").pack(side=tk.LEFT, padx=(0, 4))
        self.e_buscar_prov = ttk.Entry(frm_search, width=28)
        self.e_buscar_prov.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.e_buscar_prov.bind('<KeyRelease>', self._filtrar_proveedores)

        sb = ttk.Scrollbar(frm_l); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('ID', 'Nombre', 'Teléfono', 'Correo', 'Contacto', 'Estado')
        self.tree = ttk.Treeview(frm_l, columns=cols, show='headings',
                                  yscrollcommand=sb.set, height=20)
        sb.config(command=self.tree.yview)
        anchos = {'ID': 40, 'Nombre': 180, 'Teléfono': 100,
                  'Correo': 180, 'Contacto': 120, 'Estado': 90}
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=anchos[c], minwidth=anchos[c],
                              anchor=tk.CENTER if c in ('ID', 'Estado') else tk.W)
        self.tree.tag_configure('activo',      background='#F0FDF4', foreground='#065F46')
        self.tree.tag_configure('inhabilitado',background='#FEF2F2', foreground='#991B1B')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(self.tree)
        self.tree.bind('<<TreeviewSelect>>', self._seleccionar)

        frm_btns_l = ttk.Frame(frm_l)
        frm_btns_l.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(frm_btns_l, text="📦 Ver Productos Asociados",
                   command=self._ver_productos).pack(side=tk.LEFT, padx=(0, 4), expand=True, fill=tk.X)
        ttk.Button(frm_btns_l, text="📊 Reporte por Proveedor",
                   command=self._reporte_proveedor).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # ── Formulario ─────────────────────────────────────────────────────────
        frm_r = ttk.LabelFrame(contenedor, text="Datos del Proveedor", padding=10)
        frm_r.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 0), ipadx=4)

        st = 'normal' if self.can_edit else 'disabled'
        campos = [
            ("Nombre: *",  'e_nombre',   'entry'),
            ("RUC / NIT:", 'e_ruc',      'entry'),
            ("Teléfono:",  'e_telefono', 'entry'),
            ("Correo:",    'e_correo',   'entry'),
            ("Contacto:",  'e_contacto', 'entry'),
            ("Dirección:", 'e_direccion','text'),
        ]
        for i, (lbl, attr, tipo) in enumerate(campos):
            ttk.Label(frm_r, text=lbl).grid(row=i, column=0, sticky='nw',
                                             padx=(0, 8), pady=6)
            if tipo == 'text':
                w = tk.Text(frm_r, width=22, height=3,
                            font=('Segoe UI', 9), relief='flat', bd=1, state=st)
            else:
                w = ttk.Entry(frm_r, width=24, state=st)
            w.grid(row=i, column=1, pady=6, sticky='ew')
            setattr(self, attr, w)

        if self.can_edit:
            fila = len(campos)
            # Una sola fila con los 5 botones
            frm_btn = ttk.Frame(frm_r)
            frm_btn.grid(row=fila, column=0, columnspan=2, pady=10, sticky='ew')
            ttk.Button(frm_btn, text="➕",
                       command=self._crear,
                       style='Create.TButton').pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
            ttk.Button(frm_btn, text="✏️",
                       command=self._actualizar,
                       style='Update.TButton').pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
            ttk.Button(frm_btn, text="🚫",
                       command=self._inhabilitar,
                       style='Delete.TButton').pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
            ttk.Button(frm_btn, text="✅",
                       command=self._habilitar,
                       style='Neutral.TButton').pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
            ttk.Button(frm_btn, text="🔄",
                       command=self._limpiar,
                       style='Neutral.TButton').pack(side=tk.LEFT, padx=2)

    # ── Carga ─────────────────────────────────────────────────────────────────

    def _cargar(self):
        provs = self.db.obtener_proveedores(incluir_inactivos=True)
        self._todos_proveedores = provs
        self._poblar_tree(provs)

    def _filtrar_proveedores(self, event=None):
        termino = self.e_buscar_prov.get().strip().lower()
        if not termino:
            self._poblar_tree(self._todos_proveedores)
            return
        filtrados = [p for p in self._todos_proveedores
                     if termino in (p.get('nombre') or '').lower()
                     or termino in (p.get('correo') or '').lower()
                     or termino in (p.get('telefono') or '').lower()
                     or termino in (p.get('ruc_nit') or '').lower()]
        self._poblar_tree(filtrados)

    def _poblar_tree(self, provs):
        for i in self.tree.get_children(): self.tree.delete(i)
        for p in provs:
            activo = p.get('activo', 1)
            estado = '✅ Activo' if activo else '🚫 Inhabilitado'
            tag    = 'activo' if activo else 'inhabilitado'
            self.tree.insert('', tk.END, tags=(tag,), values=(
                p['id'], p['nombre'],
                p.get('telefono', '') or '',
                p.get('correo',   '') or '',
                p.get('contacto', '') or '',
                estado))

    def _seleccionar(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])['values']
        self.seleccionado = vals[0]

        p = self.db.obtener_proveedor(self.seleccionado)
        if not p: return

        def _set(w, val):
            if isinstance(w, tk.Text):
                w.config(state='normal')
                w.delete('1.0', tk.END)
                w.insert('1.0', val or '')
                if not self.can_edit: w.config(state='disabled')
            else:
                w.config(state='normal')
                w.delete(0, tk.END)
                w.insert(0, str(val) if val else '')
                if not self.can_edit: w.config(state='disabled')

        _set(self.e_nombre,   p['nombre'])
        if hasattr(self, 'e_ruc'): _set(self.e_ruc, p.get('ruc_nit', ''))
        _set(self.e_telefono, p.get('telefono', ''))
        _set(self.e_correo,   p.get('correo',   ''))
        _set(self.e_contacto, p.get('contacto', ''))
        _set(self.e_direccion,p.get('direccion',''))

    def _get_form(self):
        nombre = self.e_nombre.get().strip()
        if not nombre:
            raise ValueError("El nombre del proveedor es requerido.")
        return (nombre,
                self.e_ruc.get().strip() if hasattr(self, 'e_ruc') else '',
                self.e_telefono.get().strip(),
                self.e_correo.get().strip(),
                self.e_contacto.get().strip(),
                self.e_direccion.get('1.0', tk.END).strip()
                if isinstance(self.e_direccion, tk.Text)
                else self.e_direccion.get().strip())

    def _crear(self):
        try:
            n, ruc, t, c, ct, d = self._get_form()
            ok, msg = self.db.crear_proveedor(n, t, c, d, ct, ruc)
            messagebox.showinfo("✅", msg, parent=self.win) if ok \
                else messagebox.showerror("❌", msg, parent=self.win)
            if ok:
                self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                      'Crear proveedor', f'Nombre: {n}')
                self._limpiar(); self._cargar()
        except ValueError as e:
            messagebox.showwarning("⚠️", str(e), parent=self.win)

    def _actualizar(self):
        if not self.seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un proveedor.",
                                   parent=self.win); return
        try:
            n, ruc, t, c, ct, d = self._get_form()
            ok, msg = self.db.actualizar_proveedor(self.seleccionado, n, t, c, d, ct, ruc)
            messagebox.showinfo("✅", msg, parent=self.win) if ok \
                else messagebox.showerror("❌", msg, parent=self.win)
            if ok:
                self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                      'Actualizar proveedor', f'ID: {self.seleccionado}')
                self._limpiar(); self._cargar()
        except ValueError as e:
            messagebox.showwarning("⚠️", str(e), parent=self.win)

    def _inhabilitar(self):
        if not self.seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un proveedor.",
                                   parent=self.win); return

        nombre = self.e_nombre.get().strip()
        if not messagebox.askyesno("🚫 Inhabilitar proveedor",
                                   f"¿Inhabilitar '{nombre}'?\n\n"
                                   f"No aparecerá en el formulario de productos.",
                                   parent=self.win): return
        ok, msg = self.db.inhabilitar_proveedor(self.seleccionado)
        if ok:
            self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                  'Inhabilitar proveedor', f'ID: {self.seleccionado}')
            messagebox.showinfo("✅", f"Proveedor '{nombre}' inhabilitado.",
                                parent=self.win)
            self._limpiar(); self._cargar()
        else:
            messagebox.showerror("❌ No se puede inhabilitar", msg, parent=self.win)

    def _habilitar(self):
        if not self.seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un proveedor.",
                                   parent=self.win); return
        nombre = self.e_nombre.get().strip()
        ok, msg = self.db.habilitar_proveedor(self.seleccionado)
        if ok:
            self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                  'Habilitar proveedor', f'ID: {self.seleccionado}')
            messagebox.showinfo("✅", f"Proveedor '{nombre}' habilitado.",
                                parent=self.win)
            self._limpiar(); self._cargar()
        else:
            messagebox.showerror("❌", msg, parent=self.win)

    def _limpiar(self):
        self.seleccionado = None
        for attr in ('e_nombre', 'e_ruc', 'e_telefono', 'e_correo', 'e_contacto'):
            w = getattr(self, attr)
            w.config(state='normal'); w.delete(0, tk.END)
            if not self.can_edit: w.config(state='disabled')
        self.e_direccion.config(state='normal')
        self.e_direccion.delete('1.0', tk.END)
        if not self.can_edit: self.e_direccion.config(state='disabled')
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def _reporte_proveedor(self):
        """Muestra un resumen de inventario agrupado por proveedor."""
        datos = self.db.reporte_por_proveedor()
        win2  = tk.Toplevel(self.win)
        win2.title("📊 Reporte por Proveedor")
        win2.configure(bg='#F1F5F9')
        win2.grab_set()
        configurar_ventana(win2, width=980, height=620, min_width=860, min_height=540)

        tk.Label(win2, text="📊 Reporte General por Proveedor",
                 font=('Segoe UI', 13, 'bold'),
                 bg='#F1F5F9', fg='#2563EB').pack(pady=10)

        # Buscador del reporte
        frm_sb = ttk.Frame(win2); frm_sb.pack(fill=tk.X, padx=12, pady=(0,6))
        ttk.Label(frm_sb, text="🔍 Buscar proveedor:").pack(side=tk.LEFT, padx=(0,4))
        e_rep_buscar = ttk.Entry(frm_sb, width=30)
        e_rep_buscar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        frm = ttk.Frame(win2); frm.pack(fill=tk.BOTH, expand=True, padx=12)
        sb  = ttk.Scrollbar(frm); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('Proveedor', 'RUC/NIT', 'Productos', 'Stock Total', 'Valor Total', 'Críticos', 'Tel.')
        tree = ttk.Treeview(frm, columns=cols, show='headings', yscrollcommand=sb.set, height=14)
        sb.config(command=tree.yview)
        for c, w in zip(cols, (180, 100, 80, 90, 120, 70, 110)):
            tree.heading(c, text=c); tree.column(c, width=w)
        tree.tag_configure('con_criticos', foreground='#991B1B')

        def _poblar_reporte(filtro=''):
            tree.delete(*tree.get_children())
            for d in datos:
                nombre = d.get('proveedor','')
                if filtro and filtro.lower() not in nombre.lower():
                    continue
                tag = 'con_criticos' if (d.get('criticos') or 0) > 0 else ''
                tree.insert('', tk.END, tags=(tag,), values=(
                    nombre,
                    d.get('ruc_nit','') or '—',
                    d.get('total_productos', 0),
                    d.get('stock_total', 0),
                    f"${float(d.get('valor_total') or 0):.2f}",
                    d.get('criticos', 0) or 0,
                    d.get('telefono','') or '—'))

        _poblar_reporte()
        e_rep_buscar.bind('<KeyRelease>', lambda e: _poblar_reporte(e_rep_buscar.get()))
        tree.pack(fill=tk.BOTH, expand=True)
        tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(tree)

        total_val = sum(float(d.get('valor_total') or 0) for d in datos)
        tk.Label(win2, text=f"Valor total en inventario: ${total_val:.2f}",
                 font=('Segoe UI', 10, 'bold'), bg='#F1F5F9',
                 fg='#2563EB').pack(pady=6)

    def _ver_productos(self):
        if not self.seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un proveedor.",
                                   parent=self.win); return
        prods = self.db.obtener_productos_proveedor(self.seleccionado)
        nombre = self.e_nombre.get().strip()
        win2 = tk.Toplevel(self.win)
        win2.title(f"📦 Productos de {nombre}")
        win2.configure(bg='#F1F5F9')
        win2.grab_set()
        configurar_ventana(win2, width=700, height=460, min_width=620, min_height=400)
        ttk.Label(win2, text=f"📦 Productos de '{nombre}'",
                  font=('Segoe UI', 11, 'bold'),
                  background='#F1F5F9',
                  foreground='#2563EB').pack(pady=10)
        frm = ttk.Frame(win2); frm.pack(fill=tk.BOTH, expand=True, padx=12)
        sb  = ttk.Scrollbar(frm); sb.pack(side=tk.RIGHT, fill=tk.Y)
        t   = ttk.Treeview(frm, columns=('ID', 'Nombre'), show='headings',
                            yscrollcommand=sb.set, height=12)
        sb.config(command=t.yview)
        t.heading('ID',     text='ID');     t.column('ID',     width=60, anchor='center')
        t.heading('Nombre', text='Nombre'); t.column('Nombre', width=320)
        for p in prods:
            t.insert('', tk.END, values=(p['id'], p['nombre']))
        t.pack(fill=tk.BOTH, expand=True)
        ttk.Label(win2, text=f"Total: {len(prods)} producto(s)",
                  foreground='#64748B').pack(pady=6)
