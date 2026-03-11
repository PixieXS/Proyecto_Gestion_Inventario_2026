import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt


class InventoryManagementApp:
    def __init__(self, root, db, usuario_actual):
        self.root = root
        self.db = db
        self.usuario = usuario_actual        # dict con id, username, rol, permisos
        self.producto_seleccionado = None

        self.root.title(
            f"📦 Gestión de Inventario  —  {usuario_actual['nombre_completo']}  "
            f"({usuario_actual['rol']})")

        # ── Pantalla completa al iniciar ──────────────────────────────────────
        self.root.state('zoomed')           # Windows: maximizado
        self.root.minsize(1100, 650)

        # ── Paleta ────────────────────────────────────────────────────────────
        self.C = {
            'primary':   '#2563EB',
            'secondary': '#10B981',
            'danger':    '#EF4444',
            'warning':   '#F59E0B',
            'bg':        '#F1F5F9',
            'surface':   '#FFFFFF',
            'text':      '#1E293B',
            'muted':     '#64748B',
            'border':    '#E2E8F0',
            'header_bg': '#1E3A5F',
        }
        self.root.config(bg=self.C['bg'])
        self._estilos()

        from reports import ReportGenerator
        from export_excel import ExcelExporter
        from excel_analysis import ExcelAnalyzer
        self.report_gen = ReportGenerator()
        self.excel_exp = ExcelExporter()
        self._ExcelAnalyzer = ExcelAnalyzer

        self._construir_ui()
        self.cargar_productos()
        # Verificar alertas de stock al abrir
        self.root.after(1500, self.verificar_alertas_stock)

    # ── Permisos ──────────────────────────────────────────────────────────────

    def perm(self, p):
        return self.db.tiene_permiso(self.usuario, p)

    # ── Estilos ───────────────────────────────────────────────────────────────

    def _estilos(self):
        s = ttk.Style()
        s.theme_use('clam')
        C = self.C

        s.configure('TFrame',       background=C['bg'])
        s.configure('TLabel',       background=C['bg'], foreground=C['text'],  font=('Segoe UI', 9))
        s.configure('Header.TLabel',background=C['bg'], foreground=C['primary'], font=('Segoe UI', 15, 'bold'))
        s.configure('Role.TLabel',  background=C['header_bg'], foreground='#CBD5E1', font=('Segoe UI', 9))
        s.configure('TLabelframe',  background=C['bg'], foreground=C['text'],  font=('Segoe UI', 9, 'bold'), padding=2)
        s.configure('TLabelframe.Label', background=C['bg'], foreground=C['text'])
        s.configure('TEntry',       fieldbackground=C['surface'], foreground=C['text'], font=('Segoe UI', 9))
        s.configure('TCombobox',    fieldbackground=C['surface'], foreground=C['text'], font=('Segoe UI', 9))
        s.configure('Treeview',     background=C['surface'], foreground=C['text'],
                    fieldbackground=C['surface'], font=('Segoe UI', 9), rowheight=24)
        s.configure('Treeview.Heading', background=C['primary'], foreground=C['surface'],
                    font=('Segoe UI', 9, 'bold'), relief='flat')
        s.map('Treeview.Heading', background=[('active', '#1D4ED8')])
        s.map('Treeview', background=[('selected', '#DBEAFE')], foreground=[('selected', C['primary'])])
        s.configure('TScrollbar',   background='#CBD5E1', troughcolor=C['border'])
        s.configure('TNotebook',    background=C['bg'])
        s.configure('TNotebook.Tab', font=('Segoe UI', 9))

        for nombre, color in [
            ('Create', C['secondary']), ('Create2', '#059669'),
            ('Update', C['primary']),   ('Update2', '#1D4ED8'),
            ('Delete', C['danger']),    ('Delete2', '#DC2626'),
            ('Neutral', '#475569'),     ('Neutral2', '#334155'),
            ('Warn',    C['warning']),  ('Warn2',   '#D97706'),
        ]:
            if '2' not in nombre:
                s.configure(f'{nombre}.TButton', font=('Segoe UI', 9, 'bold'), padding=(8, 5))
            else:
                s.map(f'{nombre[:-1]}.TButton',
                      background=[('!active', color), ('active', color)],
                      foreground=[('!active', C['surface']), ('active', C['surface'])])

        # Botones coloreados manualmente
        for tag, fg, bg, abg in [
            ('Create.TButton',  C['surface'], C['secondary'], '#059669'),
            ('Update.TButton',  C['surface'], C['primary'],   '#1D4ED8'),
            ('Delete.TButton',  C['surface'], C['danger'],    '#DC2626'),
            ('Neutral.TButton', C['surface'], '#475569',      '#334155'),
            ('Warn.TButton',    C['surface'], C['warning'],   '#D97706'),
            ('TButton',         C['surface'], C['primary'],   '#1D4ED8'),
        ]:
            s.configure(tag, font=('Segoe UI', 9, 'bold'), padding=(8, 5))
            s.map(tag,
                  background=[('!active', bg), ('active', abg)],
                  foreground=[('!active', fg), ('active', fg)])

    # ── UI principal ──────────────────────────────────────────────────────────

    def _construir_ui(self):
        self._construir_barra_superior()
        self._construir_menu()

        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))

        # Columna izquierda (formulario)
        self.frm_izq = ttk.LabelFrame(main, text="📝 Datos del Producto", padding=14)
        self.frm_izq.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self._construir_formulario(self.frm_izq)

        # Columna derecha (tabla + movimientos + stats)
        frm_der = ttk.Frame(main)
        frm_der.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._construir_busqueda(frm_der)
        self._construir_tabla(frm_der)
        self._construir_movimientos(frm_der)
        self._construir_stats(frm_der)

    def _construir_barra_superior(self):
        """Barra de cabecera con info del usuario."""
        bar = tk.Frame(self.root, bg=self.C['header_bg'], height=44)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        tk.Label(bar, text="📦 Sistema de Gestión de Inventario",
                 font=("Segoe UI", 12, "bold"), bg=self.C['header_bg'],
                 fg='white').pack(side=tk.LEFT, padx=16)

        tk.Label(bar,
                 text=f"👤 {self.usuario['nombre_completo']}  •  🛡 {self.usuario['rol']}",
                 font=("Segoe UI", 9), bg=self.C['header_bg'], fg='#94A3B8'
                 ).pack(side=tk.RIGHT, padx=16)

    def _construir_menu(self):
        C = self.C
        def menu(**kw):
            return tk.Menu(tearoff=0, bg=C['surface'], fg=C['text'],
                           activebackground=C['primary'], activeforeground=C['surface'],
                           font=('Segoe UI', 9), **kw)

        mb = tk.Menu(self.root, bg=C['surface'], fg=C['text'],
                     activebackground=C['primary'], activeforeground=C['surface'],
                     font=('Segoe UI', 9))
        self.root.config(menu=mb)

        # ── Archivo ──
        m_arch = menu()
        mb.add_cascade(label="📁 Archivo", menu=m_arch)
        m_arch.add_command(label="🔄 Recargar datos", command=self._refrescar_todo)
        m_arch.add_separator()
        m_arch.add_command(label="🔐 Cerrar sesión", command=self._cerrar_sesion)
        m_arch.add_command(label="Salir", command=self.cerrar)

        # ── Reportes ── (Admin + Gerente)
        if self.perm('ver_reportes') or self.perm('ver_graficos'):
            m_rep = menu()
            mb.add_cascade(label="📊 Reportes", menu=m_rep)
            if self.perm('ver_reportes'):
                m_rep.add_command(label="📦 Reporte de Inventario (PDF)",
                                  command=self.gen_reporte_inventario)
                m_rep.add_command(label="📋 Reporte de Movimientos (PDF)",
                                  command=self.gen_reporte_movimientos)
                m_rep.add_command(label="📈 Reporte de Estadísticas (PDF)",
                                  command=self.gen_reporte_estadisticas)
                m_rep.add_separator()
            if self.perm('reporte_fechas'):
                m_rep.add_command(label="📆 Reporte por Rango de Fechas",
                                  command=self.reporte_rango_fechas)
                m_rep.add_separator()
            if self.perm('ver_graficos'):
                m_rep.add_command(label="📊 Ver Gráficos", command=self.abrir_graficos)
            if self.perm('analizar_excel'):
                m_rep.add_command(label="🔍 Analizar Excel",
                                  command=self.abrir_analizador_excel)

        # ── Exportar ── (Admin + Gerente parcial)
        if self.perm('exportar_inventario'):
            m_exp = menu()
            mb.add_cascade(label="📤 Exportar", menu=m_exp)
            m_exp.add_command(label="📄 Exportar Inventario (Excel)",
                              command=self.exportar_inventario)
            if self.perm('exportar_movimientos'):
                m_exp.add_command(label="📄 Exportar Movimientos (Excel)",
                                  command=self.exportar_movimientos)
            if self.perm('exportar_todo'):
                m_exp.add_command(label="📦 Exportar Todo (Excel)",
                                  command=self.exportar_todo)
            if self.perm('backup_bd'):
                m_exp.add_separator()
                m_exp.add_command(label="💾 Backup Base de Datos",
                                  command=self.backup_bd)

        # ── Administración ── (solo Admin)
        if self.perm('gestionar_usuarios'):
            m_adm = menu()
            mb.add_cascade(label="👥 Administración", menu=m_adm)
            m_adm.add_command(label="👤 Gestionar Usuarios",
                              command=self.abrir_gestion_usuarios)
            if self.perm('gestionar_roles'):
                m_adm.add_command(label="🛡 Gestionar Roles",
                                  command=self.abrir_gestion_roles)
            m_adm.add_separator()
            if self.perm('ver_proveedores'):
                m_adm.add_command(label="🏭 Gestionar Proveedores",
                                  command=self.abrir_proveedores)
            if self.perm('ver_auditoria'):
                m_adm.add_command(label="🧾 Ver Historial / Auditoría",
                                  command=self.abrir_log_actividad)

        # ── Mi cuenta ──
        m_cuenta = menu()
        mb.add_cascade(label="🔑 Mi Cuenta", menu=m_cuenta)
        m_cuenta.add_command(label="🔑 Cambiar Contraseña",
                             command=self.cambiar_password)

        # ── Ayuda ──
        m_ayuda = menu()
        mb.add_cascade(label="❓ Ayuda", menu=m_ayuda)
        m_ayuda.add_command(label="📘 Manual de Usuario", command=self._abrir_manual)
        m_ayuda.add_separator()
        m_ayuda.add_command(label="ℹ Acerca de", command=self._acerca_de)

    # ── Formulario ────────────────────────────────────────────────────────────

    def _construir_formulario(self, parent):
        can_edit = self.perm('crear_producto') or self.perm('editar_producto')
        state = 'normal' if can_edit else 'disabled'

        campos = [
            ("Nombre: *",         'e_nombre',     'entry'),
            ("Descripción:",      'e_desc',        'text'),
            ("Cantidad: *",       'e_cantidad',    'entry'),
            ("Precio Unitario: *",'e_precio',      'entry'),
            ("Stock Mínimo:",     'e_stock_min',   'entry'),
            ("Proveedor: *",      'e_proveedor',   'combo_proveedor'),
            ("Categoría:",        'e_categoria',   'combo'),
        ]

        # Mapa nombre→id para proveedores
        self._proveedores_map = {}  # {'Nombre Proveedor': id}

        for i, (lbl, attr, tipo) in enumerate(campos):
            ttk.Label(parent, text=lbl).grid(row=i, column=0, sticky='w',
                                              pady=6, padx=(0, 10))
            if tipo == 'text':
                w = tk.Text(parent, width=24, height=3, font=('Segoe UI', 9),
                            relief='flat', bd=1, bg=self.C['surface'],
                            fg=self.C['text'], state=state)
            elif tipo == 'combo_proveedor':
                # Combobox que carga proveedores desde la BD
                w = ttk.Combobox(parent, width=22,
                                 state='readonly' if can_edit else 'disabled')
                self._cargar_combo_proveedores(w)
            elif tipo == 'combo':
                w = ttk.Combobox(parent, width=22,
                                 values=['General','Electrónica','Ropa','Alimentos',
                                         'Herramientas','Limpieza','Oficina','Otro'],
                                 state='readonly' if can_edit else 'disabled')
                w.set('General')
            else:
                w = ttk.Entry(parent, width=24, state=state)
            w.grid(row=i, column=1, pady=6, sticky='ew')
            setattr(self, attr, w)

        fila = len(campos)
        ttk.Label(parent, text="* Campos obligatorios",
                  font=('Segoe UI', 8), foreground=self.C['muted']
                  ).grid(row=fila, column=0, columnspan=2, sticky='w')
        fila += 1

        # Botones
        frm_btn = ttk.Frame(parent)
        frm_btn.grid(row=fila, column=0, columnspan=2, pady=14, sticky='ew')

        if self.perm('crear_producto'):
            ttk.Button(frm_btn, text="➕ Crear", command=self.crear_producto,
                       style='Create.TButton').pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        if self.perm('editar_producto'):
            ttk.Button(frm_btn, text="✏️ Actualizar", command=self.actualizar_producto,
                       style='Update.TButton').pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        if self.perm('eliminar_producto'):
            ttk.Button(frm_btn, text="🗑️ Eliminar", command=self.eliminar_producto,
                       style='Delete.TButton').pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        ttk.Button(frm_btn, text="🔄", command=self.limpiar_campos,
                   style='Neutral.TButton').pack(side=tk.LEFT, padx=3)

        fila += 1
        # Historial rápido
        if self.perm('ver_historial_producto'):
            ttk.Button(parent, text="📋 Ver Historial del Producto",
                       command=self.ver_historial_producto
                       ).grid(row=fila, column=0, columnspan=2,
                              pady=(4, 0), sticky='ew')
            fila += 1

        # Productos críticos
        ttk.Button(parent, text="🚨 Ver Productos Críticos",
                   command=self.ver_productos_criticos,
                   style='Warn.TButton'
                   ).grid(row=fila, column=0, columnspan=2, pady=(4, 0), sticky='ew')

    # ── Helpers de proveedor ─────────────────────────────────────────────────

    def _cargar_combo_proveedores(self, combo=None):
        """Recarga los proveedores desde la BD en el combobox del formulario."""
        if combo is None:
            combo = self.e_proveedor
        provs = self.db.obtener_proveedores()
        self._proveedores_map = {p['nombre']: p['id'] for p in provs}
        nombres = list(self._proveedores_map.keys())
        combo['values'] = nombres
        return nombres

    def _refrescar_combo_proveedores(self):
        actual = self.e_proveedor.get()
        nombres = self._cargar_combo_proveedores()
        if actual in nombres:
            self.e_proveedor.set(actual)
        else:
            self.e_proveedor.set('')

    # ── Búsqueda ──────────────────────────────────────────────────────────────

    def _construir_busqueda(self, parent):
        frm = ttk.LabelFrame(parent, text="🔍 Búsqueda y Filtros", padding=8)
        frm.pack(fill=tk.X, pady=(0, 8))

        row = ttk.Frame(frm)
        row.pack(fill=tk.X)

        ttk.Label(row, text="Buscar:").pack(side=tk.LEFT, padx=(0, 5))
        self.e_buscar = ttk.Entry(row, width=25)
        self.e_buscar.pack(side=tk.LEFT, padx=(0, 10))
        self.e_buscar.bind('<KeyRelease>', self._filtrar)

        ttk.Label(row, text="Categoría:").pack(side=tk.LEFT, padx=(0, 5))
        self.cb_cat = ttk.Combobox(row, width=15, state='readonly')
        self.cb_cat.pack(side=tk.LEFT, padx=(0, 10))
        self.cb_cat.bind('<<ComboboxSelected>>', self._filtrar)

        ttk.Button(row, text="✖ Limpiar", command=self._limpiar_filtros,
                   style='Neutral.TButton').pack(side=tk.LEFT)

    # ── Tabla ─────────────────────────────────────────────────────────────────

    def _construir_tabla(self, parent):
        frm = ttk.LabelFrame(parent, text="📦 Productos Registrados", padding=8)
        frm.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        sb_y = ttk.Scrollbar(frm)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x = ttk.Scrollbar(frm, orient=tk.HORIZONTAL)
        sb_x.pack(side=tk.BOTTOM, fill=tk.X)

        cols = ('ID','Nombre','Categoría','Stock','Stock Mín','Precio','Proveedor')
        self.tree = ttk.Treeview(frm, columns=cols, show='headings',
                                  yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.config(command=self.tree.yview)
        sb_x.config(command=self.tree.xview)

        anchos = {'ID':45,'Nombre':200,'Categoría':110,'Stock':75,
                  'Stock Mín':80,'Precio':110,'Proveedor':160}
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=anchos[c],
                              anchor=tk.CENTER if c in ('ID','Stock','Stock Mín','Precio') else tk.W)

        # Tags de color para stock crítico
        self.tree.tag_configure('critico',  background='#FEE2E2', foreground='#991B1B')
        self.tree.tag_configure('advertencia', background='#FEF9C3', foreground='#854D0E')
        self.tree.tag_configure('ok',       background=self.C['surface'])

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<Double-1>', self.cargar_producto_seleccionado)

    # ── Movimientos ───────────────────────────────────────────────────────────

    def _construir_movimientos(self, parent):
        if not self.perm('registrar_movimientos'):
            return
        frm = ttk.LabelFrame(parent, text="➡️ Registrar Movimiento", padding=10)
        frm.pack(fill=tk.X, pady=(0, 8))

        row = ttk.Frame(frm)
        row.pack(fill=tk.X)

        ttk.Label(row, text="Tipo:").pack(side=tk.LEFT, padx=5)
        self.cb_tipo_mov = ttk.Combobox(row, values=['📥 Entrada','📤 Salida'],
                                         width=12, state='readonly')
        self.cb_tipo_mov.pack(side=tk.LEFT, padx=5)

        ttk.Label(row, text="Cantidad:").pack(side=tk.LEFT, padx=5)
        self.e_cant_mov = ttk.Entry(row, width=10)
        self.e_cant_mov.pack(side=tk.LEFT, padx=5)

        ttk.Label(row, text="Nota:").pack(side=tk.LEFT, padx=5)
        self.e_nota_mov = ttk.Entry(row, width=20)
        self.e_nota_mov.pack(side=tk.LEFT, padx=5)

        ttk.Button(row, text="✔️ Registrar",
                   command=self.registrar_movimiento).pack(side=tk.LEFT, padx=5)

    # ── Stats bar ─────────────────────────────────────────────────────────────

    def _construir_stats(self, parent):
        """Barra de estadísticas en 2 filas para evitar recorte."""
        self.frm_stats = ttk.LabelFrame(parent, text="📈 Estadísticas en Tiempo Real", padding=8)
        self.frm_stats.pack(fill=tk.X)

        row1 = ttk.Frame(self.frm_stats)
        row1.pack(fill=tk.X)
        row2 = ttk.Frame(self.frm_stats)
        row2.pack(fill=tk.X, pady=(4, 0))

        def stat_lbl(parent, color):
            return tk.Label(parent, text="—", font=('Segoe UI', 10, 'bold'),
                            bg=self.C['bg'], fg=color, anchor='w', padx=10)

        self.lbl_prod   = stat_lbl(row1, self.C['primary'])
        self.lbl_stock  = stat_lbl(row1, '#0F766E')
        self.lbl_valor  = stat_lbl(row1, '#7C3AED')
        self.lbl_critico= stat_lbl(row2, self.C['danger'])
        self.lbl_provs  = stat_lbl(row2, '#D97706')

        for w in (self.lbl_prod, self.lbl_stock, self.lbl_valor):
            w.pack(side=tk.LEFT, expand=True, fill=tk.X)
        for w in (self.lbl_critico, self.lbl_provs):
            w.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.actualizar_estadisticas()

    # ── Lógica de productos ───────────────────────────────────────────────────

    def cargar_productos(self):
        prods = self.db.obtener_productos()
        self._poblar_tabla(prods)
        self._refrescar_cats()
        self._refrescar_combo_proveedores()  # recargar lista de proveedores
        self.actualizar_estadisticas()

    def _poblar_tabla(self, prods):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in prods:
            cant = p['cantidad']
            minimo = p.get('stock_minimo') or 5
            if cant <= 0:
                tag = 'critico'
            elif cant <= minimo:
                tag = 'advertencia'
            else:
                tag = 'ok'
            self.tree.insert('', tk.END, tags=(tag,), values=(
                p['id'], p['nombre'],
                p.get('categoria') or 'General',
                cant, minimo,
                f"${float(p['precio_unitario']):.2f}",
                p.get('proveedor') or 'N/A',
            ))

    def _refrescar_cats(self):
        cats = self.db.obtener_categorias()
        vals = ['Todas'] + cats
        self.cb_cat['values'] = vals
        if self.cb_cat.get() not in vals:
            self.cb_cat.set('Todas')

    def _filtrar(self, event=None):
        t = self.e_buscar.get().strip()
        c = self.cb_cat.get()
        self._poblar_tabla(self.db.buscar_productos(t, c))

    def _limpiar_filtros(self):
        self.e_buscar.delete(0, tk.END)
        self.cb_cat.set('Todas')
        self.cargar_productos()

    def _refrescar_todo(self):
        self.cargar_productos()

    def cargar_producto_seleccionado(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        id_prod = self.tree.item(sel[0])['values'][0]
        p = self.db.obtener_producto(id_prod)
        if not p:
            return
        self.producto_seleccionado = id_prod

        def _set(w, val):
            if isinstance(w, tk.Text):
                w.delete('1.0', tk.END)
                w.insert('1.0', val or '')
            elif isinstance(w, ttk.Combobox):
                w.set(val or 'General')
            else:
                w.delete(0, tk.END)
                w.insert(0, str(val) if val is not None else '')

        _set(self.e_nombre,    p['nombre'])
        _set(self.e_desc,      p.get('descripcion', ''))
        _set(self.e_cantidad,  p['cantidad'])
        _set(self.e_precio,    p['precio_unitario'])
        _set(self.e_stock_min, p.get('stock_minimo', 5))
        # e_proveedor es Combobox → usar .set()
        self.e_proveedor.set(p.get('proveedor', '') or '')
        _set(self.e_categoria, p.get('categoria', 'General'))

    def _datos_formulario(self):
        nombre    = self.e_nombre.get().strip()
        desc      = self.e_desc.get('1.0', tk.END).strip()
        cant_s    = self.e_cantidad.get().strip()
        precio_s  = self.e_precio.get().strip()
        stk_s     = self.e_stock_min.get().strip()
        proveedor = self.e_proveedor.get().strip()   # nombre del proveedor seleccionado
        categoria = self.e_categoria.get().strip() or 'General'

        if not nombre:
            raise ValueError("El nombre del producto es requerido.")
        if not proveedor:
            raise ValueError("El proveedor es obligatorio.\nSeleccione uno del listado.")
        cantidad   = int(cant_s)
        precio     = float(precio_s)
        stock_min  = int(stk_s) if stk_s else 5
        if precio < 0 or cantidad < 0 or stock_min < 0:
            raise ValueError("Cantidad, Precio y Stock Mínimo no pueden ser negativos.")
        # Obtener el id del proveedor desde el mapa
        id_proveedor = getattr(self, '_proveedores_map', {}).get(proveedor)
        return nombre, desc, cantidad, precio, proveedor, categoria, stock_min, id_proveedor

    def crear_producto(self):
        try:
            n, d, c, p, prov, cat, sm, id_prov = self._datos_formulario()
            ok, msg = self.db.crear_producto(n, d, c, p, prov, cat, sm, id_prov)
            if ok:
                self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                      'Crear producto', f'Nombre: {n}', n)
                messagebox.showinfo("✅ Éxito", f"Producto creado:\n{n}")
                self.limpiar_campos()
                self.cargar_productos()
                self.verificar_alertas_stock(silencioso=True)
            else:
                messagebox.showerror("❌ Error", msg)
        except ValueError as e:
            messagebox.showwarning("⚠️ Validación", str(e))

    def actualizar_producto(self):
        if not self.producto_seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un producto (doble clic).")
            return
        if not messagebox.askyesno("Confirmar", "¿Actualizar este producto?"):
            return
        try:
            n, d, c, p, prov, cat, sm, id_prov = self._datos_formulario()
            if not messagebox.askyesno("🔒 Confirmar definitivamente",
                                       f"¿Guardar cambios en '{n}'?\nEsta acción no se puede deshacer."):
                return
            ok, msg = self.db.actualizar_producto(
                self.producto_seleccionado, n, d, c, p, prov, cat, sm, id_prov)
            if ok:
                self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                      'Actualizar producto', f'Nombre: {n}', n)
                messagebox.showinfo("✅ Éxito", msg)
                self.limpiar_campos(); self.cargar_productos()
            else:
                messagebox.showerror("❌ Error", msg)
        except ValueError as e:
            messagebox.showwarning("⚠️ Validación", str(e))

    def eliminar_producto(self):
        if not self.producto_seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un producto.")
            return
        nombre = self.e_nombre.get().strip() or f"ID {self.producto_seleccionado}"
        if not messagebox.askyesno("⚠️ Eliminar", f"¿Eliminar '{nombre}'?"):
            return
        if not messagebox.askyesno("🔒 ADVERTENCIA IRREVERSIBLE",
                                   f"Esto eliminará '{nombre}' PERMANENTEMENTE.\n"
                                   f"Solo es posible si NO tiene movimientos.\n\n"
                                   f"¿Confirmar eliminación?"):
            return
        ok, msg = self.db.eliminar_producto(self.producto_seleccionado)
        if ok:
            self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                  'Eliminar producto', f'ID: {self.producto_seleccionado}', nombre)
            messagebox.showinfo("✅", msg)
            self.limpiar_campos(); self.cargar_productos()
        else:
            messagebox.showerror("❌ Error", msg)

    def limpiar_campos(self):
        for attr in ('e_nombre', 'e_cantidad', 'e_precio', 'e_stock_min'):
            getattr(self, attr).delete(0, tk.END)
        self.e_desc.delete('1.0', tk.END)
        self.e_proveedor.set('')       # Combobox → .set()
        self.e_categoria.set('General')
        self.producto_seleccionado = None
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def registrar_movimiento(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("⚠️", "Seleccione un producto de la tabla.")
            return
        id_prod  = self.tree.item(sel[0])['values'][0]
        tipo_raw = self.cb_tipo_mov.get()
        if not tipo_raw:
            messagebox.showwarning("⚠️", "Seleccione tipo de movimiento.")
            return
        tipo = tipo_raw.split()[-1]
        try:
            cant = int(self.e_cant_mov.get().strip())
            if cant <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("⚠️", "Ingrese una cantidad entera mayor a 0.")
            return
        nota = self.e_nota_mov.get().strip()
        ok, msg = self.db.registrar_movimiento(
            id_prod, tipo, cant, nota, self.usuario['id'])
        if ok:
            self.db.registrar_log(
                self.usuario['id'], self.usuario['username'],
                f'Movimiento {tipo}', f'Cantidad: {cant}',
                str(self.tree.item(sel[0])['values'][1]))
            self.e_cant_mov.delete(0, tk.END)
            self.e_nota_mov.delete(0, tk.END)
            self.cb_tipo_mov.set('')
            self.cargar_productos()
            self.verificar_alertas_stock(silencioso=True)
        else:
            messagebox.showwarning("⚠️ Stock insuficiente", msg)

    # ── Estadísticas ──────────────────────────────────────────────────────────

    def actualizar_estadisticas(self):
        s = self.db.obtener_estadisticas()
        self.lbl_prod.config(  text=f"  📊 Productos: {s.get('total_productos',0)}")
        self.lbl_stock.config( text=f"  📦 Stock Total: {s.get('stock_total',0)}")
        self.lbl_valor.config( text=f"  💰 Valor: ${s.get('valor_total',0):.2f}")
        critico = s.get('bajo_stock', 0)
        color = self.C['danger'] if critico > 0 else self.C['muted']
        self.lbl_critico.config(text=f"  🚨 Críticos: {critico}", fg=color)
        self.lbl_provs.config( text=f"  🏭 Proveedores: {s.get('total_proveedores',0)}")

    # ── Alertas de stock ──────────────────────────────────────────────────────

    def verificar_alertas_stock(self, silencioso=False):
        criticos = self.db.obtener_productos_criticos()
        if not criticos:
            return
        if not silencioso:
            msg = "\n".join(
                f"• {p['nombre']}  (stock: {p['cantidad']} / mín: {p['stock_minimo']})"
                for p in criticos[:10])
            if len(criticos) > 10:
                msg += f"\n... y {len(criticos)-10} más"
            messagebox.showwarning(
                "🚨 Alerta de Stock Bajo",
                f"{len(criticos)} producto(s) en nivel crítico:\n\n{msg}\n\n"
                f"📧 [Simulado] Aviso de reposición generado.")
        else:
            # Solo actualizar estadísticas sin popup
            self.actualizar_estadisticas()

    def ver_productos_criticos(self):
        criticos = self.db.obtener_productos_criticos()
        win = tk.Toplevel(self.root)
        win.title("🚨 Productos con Stock Crítico")
        win.geometry("640x400")
        win.configure(bg=self.C['bg'])
        win.grab_set()

        ttk.Label(win, text=f"🚨 {len(criticos)} producto(s) en nivel crítico",
                  style='Header.TLabel').pack(pady=10, padx=12)

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        sb = ttk.Scrollbar(frm); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('Nombre','Stock Actual','Stock Mínimo','Diferencia','Proveedor')
        tree = ttk.Treeview(frm, columns=cols, show='headings',
                             yscrollcommand=sb.set)
        sb.config(command=tree.yview)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=110 if c != 'Nombre' else 200)
        tree.tag_configure('cero',  background='#FEE2E2')
        tree.tag_configure('bajo',  background='#FEF9C3')
        for p in criticos:
            dif = p['cantidad'] - p['stock_minimo']
            tag = 'cero' if p['cantidad'] <= 0 else 'bajo'
            tree.insert('', tk.END, tags=(tag,), values=(
                p['nombre'], p['cantidad'], p['stock_minimo'], dif,
                p.get('proveedor') or 'N/A'))
        tree.pack(fill=tk.BOTH, expand=True)

    # ── Historial por producto ────────────────────────────────────────────────

    def ver_historial_producto(self):
        if not self.producto_seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un producto primero.")
            return
        hist = self.db.obtener_historial_producto(self.producto_seleccionado)
        nombre = self.e_nombre.get() or f"ID {self.producto_seleccionado}"

        win = tk.Toplevel(self.root)
        win.title(f"📋 Historial — {nombre}")
        win.geometry("720x450")
        win.configure(bg=self.C['bg'])
        win.grab_set()

        ttk.Label(win, text=f"📋 Historial de movimientos: {nombre}",
                  style='Header.TLabel').pack(pady=10, padx=12)

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        sb = ttk.Scrollbar(frm); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('ID','Tipo','Cantidad','Fecha','Usuario','Nota')
        tree = ttk.Treeview(frm, columns=cols, show='headings', yscrollcommand=sb.set)
        sb.config(command=tree.yview)
        anchos = {'ID':45,'Tipo':80,'Cantidad':75,'Fecha':150,'Usuario':110,'Nota':200}
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=anchos[c])
        tree.tag_configure('entrada', foreground='#065F46')
        tree.tag_configure('salida',  foreground='#991B1B')
        for m in hist:
            tag = 'entrada' if 'entrada' in str(m.get('tipo_movimiento','')).lower() else 'salida'
            tree.insert('', tk.END, tags=(tag,), values=(
                m['id'], m['tipo_movimiento'], m['cantidad'],
                m['fecha'].strftime('%d/%m/%Y %H:%M') if m['fecha'] else '',
                m.get('usuario','Sistema'),
                m.get('descripcion','') or ''))
        tree.pack(fill=tk.BOTH, expand=True)
        ttk.Label(win, text=f"Total de movimientos: {len(hist)}",
                  foreground=self.C['muted']).pack(pady=4)

    # ── Reportes ──────────────────────────────────────────────────────────────

    def gen_reporte_inventario(self):
        prods = self.db.obtener_productos()
        if not prods:
            messagebox.showwarning("⚠️", "No hay productos."); return
        ok, msg = self.report_gen.generar_reporte_inventario(prods)
        messagebox.showinfo("✅", msg) if ok else messagebox.showerror("❌", msg)
        self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                              'Generar PDF Inventario')

    def gen_reporte_movimientos(self):
        movs = self.db.obtener_movimientos()
        if not movs:
            messagebox.showwarning("⚠️", "No hay movimientos."); return
        prods = {p['id']: p for p in self.db.obtener_productos()}
        ok, msg = self.report_gen.generar_reporte_movimientos(movs, prods)
        messagebox.showinfo("✅", msg) if ok else messagebox.showerror("❌", msg)
        self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                              'Generar PDF Movimientos')

    def gen_reporte_estadisticas(self):
        stats = self.db.obtener_estadisticas()
        ok, msg = self.report_gen.generar_reporte_estadisticas(stats)
        messagebox.showinfo("✅", msg) if ok else messagebox.showerror("❌", msg)

    def reporte_rango_fechas(self):
        win = tk.Toplevel(self.root)
        win.title("📆 Reporte por Rango de Fechas")
        win.geometry("380x200")
        win.configure(bg=self.C['bg'])
        win.grab_set()

        ttk.Label(win, text="📆 Seleccionar Rango de Fechas",
                  style='Header.TLabel').pack(pady=10)
        frm = ttk.Frame(win); frm.pack()

        ttk.Label(frm, text="Desde (YYYY-MM-DD):").grid(row=0, column=0, padx=8, pady=8, sticky='e')
        e_desde = ttk.Entry(frm, width=16)
        e_desde.insert(0, (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        e_desde.grid(row=0, column=1, pady=8)

        ttk.Label(frm, text="Hasta (YYYY-MM-DD):").grid(row=1, column=0, padx=8, pady=8, sticky='e')
        e_hasta = ttk.Entry(frm, width=16)
        e_hasta.insert(0, datetime.now().strftime('%Y-%m-%d'))
        e_hasta.grid(row=1, column=1, pady=8)

        def generar():
            fi, ff = e_desde.get().strip(), e_hasta.get().strip()
            movs = self.db.obtener_movimientos_rango(fi, ff)
            if not movs:
                messagebox.showinfo("ℹ️", "No hay movimientos en ese rango.", parent=win)
                return
            prods = {p['id']: p for p in self.db.obtener_productos()}
            ok, msg = self.report_gen.generar_reporte_movimientos(movs, prods, titulo=f"MOVIMIENTOS {fi} al {ff}")
            messagebox.showinfo("✅", msg, parent=win) if ok else messagebox.showerror("❌", msg, parent=win)
            win.destroy()

        ttk.Button(win, text="📄 Generar PDF", command=generar).pack(pady=12)

    # ── Exportar ──────────────────────────────────────────────────────────────

    def exportar_inventario(self):
        prods = self.db.obtener_productos()
        if not prods:
            messagebox.showwarning("⚠️", "No hay productos."); return
        ok, r = self.excel_exp.exportar_inventario(prods)
        messagebox.showinfo("✅", f"Guardado:\n{r}") if ok else messagebox.showerror("❌", r)
        self.db.registrar_log(self.usuario['id'], self.usuario['username'], 'Exportar Inventario Excel')

    def exportar_movimientos(self):
        movs = self.db.obtener_movimientos()
        if not movs:
            messagebox.showwarning("⚠️", "No hay movimientos."); return
        prods = {p['id']: p for p in self.db.obtener_productos()}
        ok, r = self.excel_exp.exportar_movimientos(movs, prods)
        messagebox.showinfo("✅", f"Guardado:\n{r}") if ok else messagebox.showerror("❌", r)

    def exportar_todo(self):
        prods = self.db.obtener_productos()
        movs  = self.db.obtener_movimientos()
        prods_d = {p['id']: p for p in prods}
        ok, r = self.excel_exp.exportar_completo(prods, movs, prods_d)
        messagebox.showinfo("✅", f"Guardado:\n{r}") if ok else messagebox.showerror("❌", r)
        self.db.registrar_log(self.usuario['id'], self.usuario['username'], 'Exportar Todo Excel')

    def backup_bd(self):
        from tkinter import filedialog
        ruta = filedialog.asksaveasfilename(
            defaultextension='.sql',
            filetypes=[("SQL", "*.sql"), ("Todos", "*.*")],
            initialfile=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
        if not ruta:
            return
        ok, r = self.db.backup_base_datos(ruta)
        messagebox.showinfo("✅", f"Backup guardado:\n{r}") if ok else messagebox.showerror("❌", r)
        self.db.registrar_log(self.usuario['id'], self.usuario['username'], 'Backup BD', ruta)

    # ── Gráficos ──────────────────────────────────────────────────────────────

    def abrir_graficos(self):
        win = tk.Toplevel(self.root)
        win.title("📊 Visualización de Estadísticas")
        win.geometry("1000x680")
        win.configure(bg=self.C['bg'])

        ttk.Label(win, text="📊 Análisis y Visualización",
                  style='Header.TLabel').pack(pady=10, padx=12)
        nb = ttk.Notebook(win)
        nb.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        prods = self.db.obtener_productos()

        def tab_bar(title, etiquetas, valores, xlabel):
            p = ttk.Frame(nb); nb.add(p, text=title)
            fig, ax = plt.subplots(figsize=(8, 4), facecolor=self.C['bg'])
            ax.set_facecolor(self.C['surface'])
            ax.barh(etiquetas[::-1], valores[::-1], color=self.C['secondary'])
            ax.set_title(title, fontsize=11, fontweight='bold', color=self.C['text'])
            ax.set_xlabel(xlabel, color=self.C['text'])
            ax.tick_params(colors=self.C['text'])
            fig.tight_layout()
            c = FigureCanvasTkAgg(fig, master=p)
            c.draw(); c.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab stock
        top10 = sorted(prods, key=lambda x: x.get('cantidad', 0), reverse=True)[:10]
        tab_bar("Top 10 Stock", [p['nombre'] for p in top10],
                [p['cantidad'] for p in top10], "Cantidad")

        # Tab valor
        top10v = sorted(prods, key=lambda x: float(x.get('cantidad',0))*float(x.get('precio_unitario',0)), reverse=True)[:10]
        tab_bar("Top 10 Valor ($)", [p['nombre'] for p in top10v],
                [float(p['cantidad'])*float(p['precio_unitario']) for p in top10v], "Valor $")

        # Tab proveedor (pie)
        p2 = ttk.Frame(nb); nb.add(p2, text="Por Proveedor")
        stk = {}
        for p in prods:
            pv = p.get('proveedor') or 'Sin proveedor'
            stk[pv] = stk.get(pv, 0) + (p.get('cantidad') or 0)
        fig2, ax2 = plt.subplots(figsize=(6, 5), facecolor=self.C['bg'])
        ax2.set_facecolor(self.C['surface'])
        if any(stk.values()):
            ax2.pie(list(stk.values()), labels=list(stk.keys()),
                    autopct='%1.1f%%', startangle=140)
            ax2.set_title("Distribucion de stock por proveedor",
                          fontsize=11, fontweight='bold', color=self.C['text'])
        fig2.tight_layout()
        c2 = FigureCanvasTkAgg(fig2, master=p2)
        c2.draw(); c2.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab movimientos 30 días
        p3 = ttk.Frame(nb); nb.add(p3, text="Movimientos 30 dias")
        movs = self.db.obtener_movimientos()
        hoy = datetime.now().date()
        inicio = hoy - timedelta(days=29)
        neto = {}
        for m in movs:
            f = m.get('fecha')
            if not f: continue
            fd = f.date()
            if fd < inicio or fd > hoy: continue
            t = (m.get('tipo_movimiento') or '').lower()
            c_val = int(m.get('cantidad') or 0)
            neto[fd] = neto.get(fd, 0) + (c_val if 'entrada' in t else -c_val)
        fechas = [inicio + timedelta(days=i) for i in range(30)]
        fig3, ax3 = plt.subplots(figsize=(9, 3.5), facecolor=self.C['bg'])
        ax3.set_facecolor(self.C['surface'])
        vals3 = [neto.get(d, 0) for d in fechas]
        colores3 = [self.C['secondary'] if v >= 0 else self.C['danger'] for v in vals3]
        ax3.bar(fechas, vals3, color=colores3)
        ax3.set_title('Movimiento neto diario (ultimos 30 dias)',
                      fontsize=11, fontweight='bold', color=self.C['text'])
        ax3.grid(axis='y', alpha=0.2)
        fig3.autofmt_xdate(rotation=45)
        fig3.tight_layout()
        c3 = FigureCanvasTkAgg(fig3, master=p3)
        c3.draw(); c3.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def abrir_analizador_excel(self):
        from excel_analysis import ExcelAnalyzer
        ExcelAnalyzer(self.root).open_window()

    # ── Administración ────────────────────────────────────────────────────────

    def abrir_gestion_usuarios(self):
        from users_module import UsersWindow
        UsersWindow(self.root, self.db, self.usuario)

    def abrir_gestion_roles(self):
        from users_module import RolesWindow
        RolesWindow(self.root, self.db)

    def abrir_proveedores(self):
        from suppliers_module import SuppliersWindow
        SuppliersWindow(self.root, self.db, self.usuario)
        # Refrescar el combo de proveedores del formulario al volver
        self._refrescar_combo_proveedores()

    def abrir_log_actividad(self):
        from activity_log_module import LogWindow
        LogWindow(self.root, self.db)

    # ── Mi Cuenta ─────────────────────────────────────────────────────────────

    def cambiar_password(self):
        win = tk.Toplevel(self.root)
        win.title("🔑 Cambiar Contraseña")
        win.geometry("350x230")
        win.configure(bg=self.C['bg'])
        win.grab_set()

        frm = ttk.Frame(win); frm.pack(padx=20, pady=20)
        ttk.Label(frm, text="🔑 Cambiar Contraseña",
                  style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 14))

        campos = [("Contraseña actual:", 'e_actual'),
                  ("Nueva contraseña:",  'e_nueva'),
                  ("Confirmar nueva:",   'e_confirmar')]
        entries = {}
        for i, (lbl, key) in enumerate(campos, 1):
            ttk.Label(frm, text=lbl).grid(row=i, column=0, sticky='e', padx=8, pady=6)
            e = ttk.Entry(frm, width=20, show='*')
            e.grid(row=i, column=1, pady=6)
            entries[key] = e

        msg = tk.Label(win, text='', font=('Segoe UI', 9), bg=self.C['bg'], fg=self.C['danger'])
        msg.pack()

        def guardar():
            actual  = entries['e_actual'].get()
            nueva   = entries['e_nueva'].get()
            confirm = entries['e_confirmar'].get()
            if nueva != confirm:
                msg.config(text="Las contraseñas nuevas no coinciden."); return
            if len(nueva) < 4:
                msg.config(text="La contraseña debe tener al menos 4 caracteres."); return
            ok, texto = self.db.cambiar_password(self.usuario['id'], actual, nueva)
            if ok:
                self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                      'Cambiar contraseña')
                messagebox.showinfo("✅", texto, parent=win)
                win.destroy()
            else:
                msg.config(text=texto)

        ttk.Button(win, text="Guardar", command=guardar).pack(pady=10)

    # ── Misc ──────────────────────────────────────────────────────────────────

    def _cerrar_sesion(self):
        if not messagebox.askyesno("🔐 Cerrar sesión", "¿Desea cerrar sesión?"):
            return

        # Destruir todos los widgets de la ventana actual
        for widget in self.root.winfo_children():
            widget.destroy()

        # Ocultar la ventana principal mientras aparece el login
        self.root.withdraw()

        # Reimportar mostrar_login (está en main.py)
        from main import mostrar_login
        usuario = mostrar_login(self.root, self.db)

        if not usuario:
            # Si cierra el login sin entrar → cerrar la app
            self.db.disconnect()
            self.root.destroy()
            return

        # Volver a mostrar la ventana y cargar la app con el nuevo usuario
        self.root.deiconify()
        InventoryManagementApp(self.root, self.db, usuario)

    def _abrir_manual(self):
        import os, sys, subprocess
        # Buscar el PDF relativo a la ubicacion del script
        base = os.path.dirname(os.path.abspath(__file__))
        ruta = os.path.join(base, 'manual_usuario.pdf')
        if not os.path.exists(ruta):
            messagebox.showwarning(
                "⚠️ Manual no encontrado",
                f"No se encontro el archivo manual_usuario.pdf.\n"
                f"Asegurese de que este en la carpeta del programa:\n{base}")
            return
        try:
            if sys.platform == 'win32':
                os.startfile(ruta)          # Windows: abre con el visor PDF por defecto
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', ruta])   # macOS
            else:
                subprocess.Popen(['xdg-open', ruta])  # Linux
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo abrir el manual:\n{e}")

    def _acerca_de(self):
        messagebox.showinfo("ℹ️ Acerca de",
                            "📦 Sistema de Gestión de Inventario\n\n"
                            "Versión: 2.0\n"
                            "Python + Tkinter + MySQL\n\n"
                            "Módulos:\n"
                            "  • Roles y permisos en BD\n"
                            "  • Módulo de Proveedores\n"
                            "  • Alertas inteligentes de stock\n"
                            "  • Historial por producto\n"
                            "  • Auditoría de actividad\n"
                            "  • Reportes PDF/Excel\n\n"
                            "© 2026 - Equipo STS")

    def cerrar(self):
        self.db.disconnect()
        self.root.quit()
