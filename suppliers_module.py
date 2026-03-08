import tkinter as tk
from tkinter import ttk, messagebox


class SuppliersWindow:
    """Ventana para gestionar proveedores."""

    def __init__(self, master, db, usuario):
        self.db = db
        self.usuario = usuario
        self.seleccionado = None
        self.can_edit = db.tiene_permiso(usuario, 'gestionar_proveedores')

        self.win = tk.Toplevel(master)
        self.win.title("🏭 Gestión de Proveedores")
        self.win.geometry("960x540")
        self.win.configure(bg='#F1F5F9')
        self.win.grab_set()

        self._build()
        self._cargar()

    def _build(self):
        ttk.Label(self.win, text="🏭 Gestión de Proveedores",
                  font=('Segoe UI', 13, 'bold'), background='#F1F5F9',
                  foreground='#2563EB').pack(pady=(12, 6), padx=14)

        paned = ttk.PanedWindow(self.win, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        # ── Lista ──────────────────────────────────────────────────────────────
        frm_l = ttk.LabelFrame(paned, text="Proveedores", padding=8)
        paned.add(frm_l, weight=3)

        sb = ttk.Scrollbar(frm_l); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('ID','Nombre','Teléfono','Correo','Contacto')
        self.tree = ttk.Treeview(frm_l, columns=cols, show='headings',
                                  yscrollcommand=sb.set, height=16)
        sb.config(command=self.tree.yview)
        anchos = {'ID':40,'Nombre':180,'Teléfono':100,'Correo':180,'Contacto':120}
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=anchos[c], anchor=tk.CENTER if c=='ID' else tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', self._seleccionar)

        # Botón ver productos asociados
        ttk.Button(frm_l, text="📦 Ver Productos Asociados",
                   command=self._ver_productos).pack(pady=(6, 0))

        # ── Formulario ─────────────────────────────────────────────────────────
        frm_r = ttk.LabelFrame(paned, text="Datos del Proveedor", padding=10)
        paned.add(frm_r, weight=2)

        st = 'normal' if self.can_edit else 'disabled'
        campos = [
            ("Nombre: *",   'e_nombre',   'entry'),
            ("Teléfono:",   'e_telefono', 'entry'),
            ("Correo:",     'e_correo',   'entry'),
            ("Contacto:",   'e_contacto', 'entry'),
            ("Dirección:",  'e_direccion','text'),
        ]
        for i, (lbl, attr, tipo) in enumerate(campos):
            ttk.Label(frm_r, text=lbl).grid(row=i, column=0, sticky='nw',
                                             padx=(0, 8), pady=6)
            if tipo == 'text':
                w = tk.Text(frm_r, width=22, height=3, font=('Segoe UI', 9),
                            relief='flat', bd=1, state=st)
            else:
                w = ttk.Entry(frm_r, width=24, state=st)
            w.grid(row=i, column=1, pady=6, sticky='ew')
            setattr(self, attr, w)

        fila = len(campos)
        if self.can_edit:
            frm_btn = ttk.Frame(frm_r)
            frm_btn.grid(row=fila, column=0, columnspan=2, pady=14, sticky='ew')
            ttk.Button(frm_btn, text="➕ Crear",
                       command=self._crear).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
            ttk.Button(frm_btn, text="✏️ Actualizar",
                       command=self._actualizar).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
            ttk.Button(frm_btn, text="🗑️ Eliminar",
                       command=self._eliminar).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
            ttk.Button(frm_btn, text="🔄",
                       command=self._limpiar).pack(side=tk.LEFT, padx=3)

    def _cargar(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in self.db.obtener_proveedores():
            self.tree.insert('', tk.END, values=(
                p['id'], p['nombre'], p.get('telefono','') or '',
                p.get('correo','') or '', p.get('contacto','') or ''))

    def _seleccionar(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])['values']
        self.seleccionado = vals[0]
        # Recuperar datos completos
        provs = self.db.obtener_proveedores()
        prov = next((p for p in provs if p['id'] == vals[0]), None)
        if not prov: return

        def _set(w, val):
            st = w.cget('state') if hasattr(w, 'cget') else 'normal'
            if isinstance(w, tk.Text):
                w.config(state='normal')
                w.delete('1.0', tk.END)
                w.insert('1.0', val or '')
                if st == 'disabled': w.config(state='disabled')
            else:
                w.config(state='normal')
                w.delete(0, tk.END)
                w.insert(0, str(val) if val else '')
                if st == 'disabled': w.config(state='disabled')

        _set(self.e_nombre,   prov['nombre'])
        _set(self.e_telefono, prov.get('telefono',''))
        _set(self.e_correo,   prov.get('correo',''))
        _set(self.e_contacto, prov.get('contacto',''))
        _set(self.e_direccion,prov.get('direccion',''))

    def _get_form(self):
        nombre = self.e_nombre.get().strip()
        if not nombre:
            raise ValueError("El nombre del proveedor es requerido.")
        return (
            nombre,
            self.e_telefono.get().strip(),
            self.e_correo.get().strip(),
            self.e_direccion.get('1.0', tk.END).strip(),
            self.e_contacto.get().strip(),
        )

    def _crear(self):
        try:
            n, t, c, d, ct = self._get_form()
            ok, msg = self.db.crear_proveedor(n, t, c, d, ct)
            if ok:
                messagebox.showinfo("✅", msg, parent=self.win)
                self._limpiar(); self._cargar()
            else:
                messagebox.showerror("❌", msg, parent=self.win)
        except ValueError as e:
            messagebox.showwarning("⚠️", str(e), parent=self.win)

    def _actualizar(self):
        if not self.seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un proveedor.", parent=self.win); return
        try:
            n, t, c, d, ct = self._get_form()
            ok, msg = self.db.actualizar_proveedor(self.seleccionado, n, t, c, d, ct)
            if ok:
                messagebox.showinfo("✅", msg, parent=self.win)
                self._limpiar(); self._cargar()
            else:
                messagebox.showerror("❌", msg, parent=self.win)
        except ValueError as e:
            messagebox.showwarning("⚠️", str(e), parent=self.win)

    def _eliminar(self):
        if not self.seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un proveedor.", parent=self.win); return

        # FIX: verificar si tiene productos asociados antes de eliminar
        prods = self.db.obtener_productos_proveedor(self.seleccionado)
        if prods:
            nombres = "\n".join(f"  • {p['nombre']}" for p in prods[:5])
            extra = f"\n  ...y {len(prods)-5} más" if len(prods) > 5 else ""
            messagebox.showerror(
                "❌ No se puede eliminar",
                f"Este proveedor tiene {len(prods)} producto(s) asociado(s):\n\n"
                f"{nombres}{extra}\n\n"
                f"Reasigne o elimine esos productos primero.",
                parent=self.win)
            return

        if not messagebox.askyesno("Eliminar", "¿Eliminar este proveedor?\n"
                                   "Esta acción no se puede deshacer.",
                                   parent=self.win): return
        ok, msg = self.db.eliminar_proveedor(self.seleccionado)
        if ok:
            messagebox.showinfo("✅", msg, parent=self.win)
            self._limpiar(); self._cargar()
        else:
            messagebox.showerror("❌", msg, parent=self.win)

    def _limpiar(self):
        for attr in ('e_nombre','e_telefono','e_correo','e_contacto'):
            w = getattr(self, attr)
            w.config(state='normal')
            w.delete(0, tk.END)
            if not self.can_edit: w.config(state='disabled')
        self.e_direccion.config(state='normal')
        self.e_direccion.delete('1.0', tk.END)
        if not self.can_edit: self.e_direccion.config(state='disabled')
        self.seleccionado = None
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def _ver_productos(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("⚠️", "Seleccione un proveedor.", parent=self.win); return
        id_prov = self.tree.item(sel[0])['values'][0]
        nombre_prov = self.tree.item(sel[0])['values'][1]
        prods = self.db.obtener_productos_proveedor(id_prov)

        win2 = tk.Toplevel(self.win)
        win2.title(f"📦 Productos de {nombre_prov}")
        win2.geometry("400x300")
        win2.grab_set()

        ttk.Label(win2, text=f"Productos vinculados a: {nombre_prov}",
                  font=('Segoe UI', 10, 'bold')).pack(pady=10, padx=10)

        if not prods:
            ttk.Label(win2, text="Ningún producto vinculado a este proveedor.",
                      foreground='#64748B').pack(pady=20)
            return

        frm = ttk.Frame(win2); frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        sb = ttk.Scrollbar(frm); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('ID','Nombre')
        t = ttk.Treeview(frm, columns=cols, show='headings', yscrollcommand=sb.set)
        sb.config(command=t.yview)
        t.heading('ID', text='ID'); t.column('ID', width=50)
        t.heading('Nombre', text='Nombre'); t.column('Nombre', width=300)
        for p in prods:
            t.insert('', tk.END, values=(p['id'], p['nombre']))
        t.pack(fill=tk.BOTH, expand=True)
