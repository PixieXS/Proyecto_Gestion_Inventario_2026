import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from modulos.campos_opcionales import obtener_campos_activos
from gui.ui_helpers import bloquear_columnas, configurar_ventana, pedir_confirmacion_password


def _formatear_moneda(valor):
    try:
        return f"${float(valor):.2f}"
    except (TypeError, ValueError):
        return "--"


def _valor_tabla(valor, fallback=''):
    return fallback if valor in (None, '') else valor



class InventarioMixin:

    def _construir_formulario(self, outer_parent):
        can_edit = self.perm('crear_producto') or self.perm('editar_producto')
        state    = 'normal' if can_edit else 'disabled'
        self._proveedores_map = {}

        cvs = tk.Canvas(outer_parent, bg=self.C['bg'], highlightthickness=0, width=260)
        vsb = ttk.Scrollbar(outer_parent, orient='vertical', command=cvs.yview)
        cvs.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        cvs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        parent = tk.Frame(cvs, bg=self.C['bg'])
        win_id = cvs.create_window((0, 0), window=parent, anchor='nw')
        parent.bind('<Configure>', lambda e: cvs.configure(scrollregion=cvs.bbox('all')))
        cvs.bind('<Configure>', lambda e: cvs.itemconfig(win_id, width=e.width))
        cvs.bind('<MouseWheel>', lambda e: cvs.yview_scroll(int(-1*(e.delta/120)), 'units'))

        pad = tk.Frame(parent, bg=self.C['bg'])
        pad.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        UNIDADES = ['Unidad', 'Caja', 'Docena', 'Kg', 'Gramo', 'Litro', 'Metro',
                    'Paquete', 'Par', 'Rollo', 'Saco', 'Galón']

        campos = [
            ("Código / SKU *",  'e_codigo',        'entry'),
            ("Nombre *",        'e_nombre',        'entry'),
            ("Descripción",     'e_desc',          'text'),
            ("Cantidad *",      'e_cantidad',      'entry'),
            ("Precio Compra",   'e_precio_compra', 'entry'),
            ("Precio Venta *",  'e_precio',        'entry'),
            ("Stock Mínimo *",  'e_stock_min',     'entry'),
            ("Stock Máximo *",  'e_stock_max',     'entry'),
            ("Unidad medida *", 'e_unidad',        'combo_unidad'),
            ("Proveedor *",     'e_proveedor',     'combo_proveedor'),
            ("Categoría *",     'e_categoria',     'combo'),
        ]

        # Agregar campos opcionales activos al formulario
        self._campos_opcionales_activos = obtener_campos_activos(self.db)
        for c in self._campos_opcionales_activos:
            campos.append((c['label'], f"e_opt_{c['key']}", 'entry'))

        for lbl_txt, attr, tipo in campos:
            tk.Label(pad, text=lbl_txt, font=('Segoe UI', 8),
                     bg=self.C['bg'], fg=self.C['muted'], anchor='w').pack(fill=tk.X)

            if tipo == 'text':
                w = tk.Text(pad, width=28, height=2, font=('Segoe UI', 9),
                            relief='flat', bd=0,
                            bg=self.C['surface'], fg=self.C['text'],
                            insertbackground=self.C['text'],
                            state=state, highlightthickness=1,
                            highlightbackground=self.C['border'])
            elif tipo == 'combo_proveedor':
                w = ttk.Combobox(pad, width=26,
                                 state='readonly' if can_edit else 'disabled')
                self._cargar_combo_proveedores(w)
            elif tipo == 'combo_unidad':
                w = ttk.Combobox(pad, width=26, values=UNIDADES,
                                 state='normal' if can_edit else 'disabled')
                w.set('')
            elif tipo == 'combo':
                cats = self.db.obtener_nombres_categorias()
                vals_cat = [''] + [c for c in cats if c]
                w = ttk.Combobox(pad, width=26, values=vals_cat,
                                 state='readonly' if can_edit else 'disabled')
                w.set('')
            else:
                w = ttk.Entry(pad, width=28, state=state)

            w.pack(fill=tk.X, pady=(0, 5))
            setattr(self, attr, w)

        tk.Frame(pad, bg=self.C['border'], height=1).pack(fill=tk.X, pady=(4, 8))

        frm_btn = tk.Frame(pad, bg=self.C['bg'])
        frm_btn.pack(fill=tk.X, pady=(0, 2))

        if self.perm('crear_producto'):
            ttk.Button(frm_btn, text="➕ Crear", command=self.crear_producto,
                       style='Create.TButton').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        if self.perm('editar_producto'):
            ttk.Button(frm_btn, text="✏️ Actualizar", command=self.actualizar_producto,
                       style='Update.TButton').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(frm_btn, text="🔄", command=self.limpiar_campos,
                   style='Neutral.TButton').pack(side=tk.LEFT, padx=(2, 0))

        if self.perm('inhabilitar_producto'):
            ttk.Button(pad, text="🚫 Inhabilitar", command=self.inhabilitar_producto,
                       style='Delete.TButton').pack(fill=tk.X, pady=(2, 0))

        tk.Label(pad, text="* Campos obligatorios",
                 font=('Segoe UI', 7), bg=self.C['bg'],
                 fg=self.C['muted'], anchor='w').pack(fill=tk.X, pady=(2, 6))

        if self.perm('crear_producto'):
            ttk.Button(pad, text="📋 Agregar varios productos",
                       command=self.abrir_ingreso_masivo).pack(fill=tk.X, pady=(0, 2))

        if self.perm('ver_historial_producto'):
            ttk.Button(pad, text="📋 Historial movimientos",
                       command=self.ver_historial_producto).pack(fill=tk.X, pady=(0, 2))

        if self.perm('ver_historial_producto'):
            ttk.Button(pad, text="💰 Historial de precios",
                       command=self.ver_historial_precios).pack(fill=tk.X, pady=(0, 2))

        ttk.Button(pad, text="🚨 Críticos", command=self.ver_productos_criticos,
                   style='Warn.TButton').pack(fill=tk.X, pady=(0, 2))

        if self.perm('inhabilitar_producto'):
            ttk.Button(pad, text="🔄 Inhabilitados",
                       command=self.ver_productos_inactivos,
                       style='Neutral.TButton').pack(fill=tk.X)

    # ── Combos ────────────────────────────────────────────────────────────────

    def _cargar_combo_proveedores(self, combo=None):
        if combo is None:
            combo = self.e_proveedor
        provs = self.db.obtener_proveedores()
        self._proveedores_map = {p['nombre']: p['id'] for p in provs}
        combo['values'] = list(self._proveedores_map.keys())
        return list(self._proveedores_map.keys())

    def _refrescar_combo_proveedores(self):
        actual  = self.e_proveedor.get()
        nombres = self._cargar_combo_proveedores()
        self.e_proveedor.set(actual if actual in nombres else '')

    # ── Búsqueda con filtros extendidos ───────────────────────────────────────

    def _construir_busqueda(self, parent):
        frm = ttk.LabelFrame(parent, text="🔍 Búsqueda y Filtros", padding=8)
        frm.pack(fill=tk.X, pady=(0, 8))

        row1 = ttk.Frame(frm); row1.pack(fill=tk.X, pady=(0, 4))
        row2 = ttk.Frame(frm); row2.pack(fill=tk.X)

        # Fila 1: busqueda por texto + categoría + proveedor + botón limpiar
        ttk.Label(row1, text="Buscar:").pack(side=tk.LEFT, padx=(0, 4))
        self.e_buscar = ttk.Entry(row1, width=20)
        self.e_buscar.pack(side=tk.LEFT, padx=(0, 8))
        self.e_buscar.bind('<KeyRelease>', self._filtrar)

        ttk.Label(row1, text="Categoría:").pack(side=tk.LEFT, padx=(0, 4))
        self.cb_cat = ttk.Combobox(row1, width=13, state='readonly')
        self.cb_cat.pack(side=tk.LEFT, padx=(0, 8))
        self.cb_cat.bind('<<ComboboxSelected>>', self._filtrar)

        ttk.Label(row1, text="Proveedor:").pack(side=tk.LEFT, padx=(0, 4))
        self.cb_prov_filtro = ttk.Combobox(row1, width=14, state='readonly')
        self.cb_prov_filtro.pack(side=tk.LEFT, padx=(0, 8))
        self.cb_prov_filtro.bind('<<ComboboxSelected>>', self._filtrar)

        ttk.Button(row1, text="✖ Limpiar", command=self._limpiar_filtros,
                   style='Neutral.TButton').pack(side=tk.LEFT)

        # Fila 2: rango de precio + estado de stock
        ttk.Label(row2, text="Precio min:").pack(side=tk.LEFT, padx=(0, 4))
        self.e_precio_min = ttk.Entry(row2, width=8)
        self.e_precio_min.pack(side=tk.LEFT, padx=(0, 4))
        self.e_precio_min.bind('<KeyRelease>', self._filtrar)

        ttk.Label(row2, text="Precio max:").pack(side=tk.LEFT, padx=(0, 4))
        self.e_precio_max = ttk.Entry(row2, width=8)
        self.e_precio_max.pack(side=tk.LEFT, padx=(0, 10))
        self.e_precio_max.bind('<KeyRelease>', self._filtrar)

        ttk.Label(row2, text="Estado stock:").pack(side=tk.LEFT, padx=(0, 4))
        self.cb_stock_estado = ttk.Combobox(
            row2, width=14, state='readonly',
            values=['Todos', 'Sin stock', 'Crítico', 'Normal', 'Con stock máx.'])
        self.cb_stock_estado.set('Todos')
        self.cb_stock_estado.pack(side=tk.LEFT, padx=(0, 8))
        self.cb_stock_estado.bind('<<ComboboxSelected>>', self._filtrar)

        # Paginación
        self._pagina_actual       = 0
        self._page_size           = 100
        self._productos_filtrados = []
        frm_pag = ttk.Frame(frm); frm_pag.pack(fill=tk.X, pady=(4, 0))
        self.lbl_paginacion = tk.Label(frm_pag, text="",
                                       font=('Segoe UI', 8),
                                       bg=self.C['bg'], fg=self.C['muted'])
        self.lbl_paginacion.pack(side=tk.LEFT)

        self._btn_prev = ttk.Button(frm_pag, text="◀ Anterior",
                                    command=self._pagina_anterior,
                                    style='Neutral.TButton')
        self._btn_prev.pack(side=tk.RIGHT, padx=2)
        self._btn_next = ttk.Button(frm_pag, text="Siguiente ▶",
                                    command=self._pagina_siguiente,
                                    style='Neutral.TButton')
        self._btn_next.pack(side=tk.RIGHT, padx=2)

    # ── Tabla ─────────────────────────────────────────────────────────────────

    def _construir_tabla(self, parent):
        frm = ttk.LabelFrame(parent, text="📦 Productos Registrados", padding=8)
        frm.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        sb_y = ttk.Scrollbar(frm); sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x = ttk.Scrollbar(frm, orient=tk.HORIZONTAL); sb_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Columnas fijas + opcionales activas
        _base_cols = ('ID', 'Código', 'Nombre', 'Categoría', 'Stock', 'Stock Mín', 'Stock Máx',
                      'Precio', 'Unidad', 'Proveedor')
        _opt_activos = getattr(self, '_campos_opcionales_activos', [])
        _opt_col_keys  = [c['col_tabla'] for c in _opt_activos]
        _opt_col_map   = {c['col_tabla']: c['key'] for c in _opt_activos}
        cols = _base_cols + tuple(_opt_col_keys)
        self._cols_opt_tabla = _opt_col_map  # guardamos para _poblar_tabla
        _base_cols = (
            'ID', 'Codigo', 'Nombre', 'Descripcion', 'Categoria',
            'Stock', 'Stock Min', 'Stock Max', 'Precio Compra',
            'Precio Venta', 'Unidad', 'Proveedor'
        )
        cols = _base_cols + tuple(_opt_col_keys)
        self._keys_opt_tabla = [c['key'] for c in _opt_activos]

        self.tree = ttk.Treeview(frm, columns=cols, show='headings',
                                  yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.config(command=self.tree.yview)
        sb_x.config(command=self.tree.xview)

        anchos = {'ID': 40, 'Código': 90, 'Nombre': 170, 'Categoría': 95,
                  'Stock': 60, 'Stock Mín': 75, 'Stock Máx': 75,
                  'Precio': 90, 'Unidad': 70, 'Proveedor': 150}
        for c in _opt_activos:
            anchos[c['col_tabla']] = c.get('ancho', 100)
        center  = ('ID', 'Stock', 'Stock Mín', 'Stock Máx', 'Precio', 'Unidad')
        num_cols = {'ID', 'Stock', 'Stock Mín', 'Stock Máx', 'Precio'}

        # _sort_state: True = próximo clic ordena ASC, False = DESC
        # Numéricas inician DESC (mayor→menor), texto inicia ASC (A→Z)
        anchos = {
            'ID': 40, 'Codigo': 110, 'Nombre': 170, 'Descripcion': 220,
            'Categoria': 110, 'Stock': 60, 'Stock Min': 75, 'Stock Max': 75,
            'Precio Compra': 105, 'Precio Venta': 105, 'Unidad': 90, 'Proveedor': 150,
        }
        for c in _opt_activos:
            anchos[c['col_tabla']] = c.get('ancho', 100)
        center = ('ID', 'Stock', 'Stock Min', 'Stock Max', 'Precio Compra', 'Precio Venta', 'Unidad')
        num_cols = {'ID', 'Stock', 'Stock Min', 'Stock Max', 'Precio Compra', 'Precio Venta'}
        self._sort_state = {c: (c not in num_cols) for c in cols}

        for c in cols:
            self.tree.heading(c, text=c,
                               command=lambda col=c, num=(c in num_cols):
                                   self._ordenar_tabla(col, num))
            self.tree.column(c, width=anchos[c], minwidth=anchos[c],
                              stretch=False,
                              anchor=tk.CENTER if c in center else tk.W)

        self.tree.tag_configure('critico',     background='#FEE2E2', foreground='#991B1B')
        self.tree.tag_configure('advertencia', background='#FEF9C3', foreground='#854D0E')
        self.tree.tag_configure('ok',          background=self.C['surface'])
        self.tree.tag_configure('sobre_max',   background='#EDE9FE', foreground='#5B21B6')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(self.tree)
        self.tree.bind('<Double-1>', self.cargar_producto_seleccionado)

    def _ordenar_tabla(self, col, es_numerica):
        """Ordena la tabla al hacer clic en el encabezado, alternando asc/desc."""
        asc = self._sort_state.get(col, True)
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]

        if es_numerica:
            def _num(v):
                try: return float(str(v).replace('$','').replace(',','').strip())
                except: return 0.0
            items.sort(key=lambda x: _num(x[0]), reverse=not asc)
        else:
            items.sort(key=lambda x: str(x[0]).lower(), reverse=not asc)

        for i, (_, k) in enumerate(items):
            self.tree.move(k, '', i)

        # Actualizar flechas en encabezados
        for c in self.tree['columns']:
            txt = self.tree.heading(c)['text'].replace(' ↑','').replace(' ↓','')
            self.tree.heading(c, text=txt)
        base = col.replace(' ↑','').replace(' ↓','')
        self.tree.heading(col, text=base + (' ↑' if asc else ' ↓'))
        self._sort_state[col] = not asc

    # ── Movimientos ───────────────────────────────────────────────────────────

    def _construir_movimientos(self, parent):
        if not self.perm('registrar_movimientos'):
            return
        frm = ttk.LabelFrame(parent, text="➡️ Registrar Movimiento", padding=10)
        frm.pack(fill=tk.X, pady=(0, 8))

        # Label del producto seleccionado
        self.lbl_prod_mov = ttk.Label(frm,
                                       text="📦 Producto: — (seleccione uno de la tabla)",
                                       foreground='#64748B',
                                       font=('Segoe UI', 9, 'italic'))
        self.lbl_prod_mov.pack(anchor='w', padx=5, pady=(0, 6))

        row = ttk.Frame(frm); row.pack(fill=tk.X)

        ttk.Label(row, text="Tipo:").pack(side=tk.LEFT, padx=5)
        self.cb_tipo_mov = ttk.Combobox(row, values=['📥 Entrada', '📤 Salida'],
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

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _construir_stats(self, parent):
        self.frm_stats = ttk.LabelFrame(parent, text="📈 Estadísticas en Tiempo Real", padding=8)
        self.frm_stats.pack(fill=tk.X)
        row1 = ttk.Frame(self.frm_stats); row1.pack(fill=tk.X)
        row2 = ttk.Frame(self.frm_stats); row2.pack(fill=tk.X, pady=(4, 0))

        def lbl(p, color):
            return tk.Label(p, text="—", font=('Segoe UI', 10, 'bold'),
                            bg=self.C['bg'], fg=color, anchor='w', padx=10)

        self.lbl_prod    = lbl(row1, self.C['primary'])
        self.lbl_stock   = lbl(row1, '#0F766E')
        self.lbl_valor   = lbl(row1, '#7C3AED')
        self.lbl_critico = lbl(row2, self.C['danger'])
        self.lbl_provs   = lbl(row2, '#D97706')

        for w in (self.lbl_prod, self.lbl_stock, self.lbl_valor):
            w.pack(side=tk.LEFT, expand=True, fill=tk.X)
        for w in (self.lbl_critico, self.lbl_provs):
            w.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.actualizar_estadisticas()

    # ── Carga y filtrado ──────────────────────────────────────────────────────

    def cargar_productos(self):
        self._pagina_actual = 0
        self._todos_los_productos = self.db.obtener_productos()
        self._productos_filtrados = list(self._todos_los_productos)
        self._poblar_tabla(self._productos_filtrados)
        self._refrescar_cats()
        self._refrescar_combo_proveedores()
        self._refrescar_proveedores_filtro()
        self.actualizar_estadisticas()

    def _refrescar_proveedores_filtro(self):
        provs = self.db.obtener_proveedores()
        vals  = ['Todos'] + [p['nombre'] for p in provs]
        self.cb_prov_filtro['values'] = vals
        if self.cb_prov_filtro.get() not in vals:
            self.cb_prov_filtro.set('Todos')

    def _poblar_tabla(self, prods):
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Paginación
        total    = len(prods)
        start    = self._pagina_actual * self._page_size
        end      = start + self._page_size
        pagina   = prods[start:end]
        total_pags = max(1, (total + self._page_size - 1) // self._page_size)
        inicio_mostrado = start + 1 if total else 0
        fin_mostrado = min(end, total)

        try:
            self.lbl_paginacion.config(
                text=f"Mostrando {start+1}–{min(end, total)} de {total} productos  |  Página {self._pagina_actual+1}/{total_pags}")
            self._btn_prev.state(['!disabled'] if self._pagina_actual > 0 else ['disabled'])
            self._btn_next.state(['!disabled'] if end < total else ['disabled'])
            self.lbl_paginacion.config(
                text=f"Mostrando {inicio_mostrado}-{fin_mostrado} de {total} productos  |  Pagina {self._pagina_actual+1}/{total_pags}")
        except Exception:
            pass

        for p in pagina:
            cant      = p['cantidad']
            minimo    = p.get('stock_minimo') or 5
            maximo    = p.get('stock_maximo')
            if cant <= 0:
                tag = 'critico'
            elif cant <= minimo:
                tag = 'advertencia'
            elif maximo and cant > maximo:
                tag = 'sobre_max'
            else:
                tag = 'ok'

            # Valores de campos opcionales
            _opt_vals = tuple(
                _valor_tabla(p.get(key), '') for key in getattr(self, '_keys_opt_tabla', [])
            )
            self.tree.insert('', tk.END, tags=(tag,), values=(
                p['id'],
                p.get('codigo') or '',
                p['nombre'],
                p.get('descripcion') or '',
                p.get('categoria') or '',
                cant, minimo,
                p.get('stock_maximo') or '—',
                _formatear_moneda(p.get('precio_compra')) or 'â€”',
                _formatear_moneda(p.get('precio_unitario')),
                p.get('unidad_medida') or 'Unidad',
                p.get('proveedor') or 'N/A') + _opt_vals)

    def _pagina_anterior(self):
        if self._pagina_actual > 0:
            self._pagina_actual -= 1
            self._poblar_tabla(self._productos_filtrados)

    def _pagina_siguiente(self):
        total = len(self._productos_filtrados)
        if (self._pagina_actual + 1) * self._page_size < total:
            self._pagina_actual += 1
            self._poblar_tabla(self._productos_filtrados)

    def _refrescar_cats(self):
        cats = self.db.obtener_categorias()
        nombres = sorted({(c['nombre'] if isinstance(c, dict) else c) for c in cats if (c['nombre'] if isinstance(c, dict) else c)})

        vals_filtro = ['Todas'] + nombres
        self.cb_cat['values'] = vals_filtro
        if self.cb_cat.get() not in vals_filtro:
            self.cb_cat.set('Todas')

        if hasattr(self, 'e_categoria'):
            actual = self.e_categoria.get().strip()
            vals_form = [''] + nombres
            if actual and actual not in vals_form:
                vals_form.append(actual)
            self.e_categoria['values'] = vals_form
            if actual not in vals_form:
                self.e_categoria.set('')

    def _filtrar(self, event=None):
        self._pagina_actual = 0
        termino    = self.e_buscar.get().strip()
        categoria  = self.cb_cat.get()
        proveedor  = self.cb_prov_filtro.get() if hasattr(self, 'cb_prov_filtro') else 'Todos'
        estado_stk = self.cb_stock_estado.get() if hasattr(self, 'cb_stock_estado') else 'Todos'

        try:
            precio_min = float(self.e_precio_min.get()) if self.e_precio_min.get().strip() else None
            precio_max = float(self.e_precio_max.get()) if self.e_precio_max.get().strip() else None
        except ValueError:
            precio_min = precio_max = None

        prods = self.db.buscar_productos(termino, categoria,
                                          proveedor=proveedor if proveedor != 'Todos' else '')

        # Filtro precio
        if precio_min is not None:
            prods = [p for p in prods if float(p['precio_unitario']) >= precio_min]
        if precio_max is not None:
            prods = [p for p in prods if float(p['precio_unitario']) <= precio_max]

        # Filtro estado stock
        if estado_stk == 'Sin stock':
            prods = [p for p in prods if p['cantidad'] <= 0]
        elif estado_stk == 'Crítico':
            prods = [p for p in prods if 0 < p['cantidad'] <= (p.get('stock_minimo') or 5)]
        elif estado_stk == 'Normal':
            prods = [p for p in prods if p['cantidad'] > (p.get('stock_minimo') or 5)]
        elif estado_stk == 'Con stock máx.':
            prods = [p for p in prods if p.get('stock_maximo') and p['cantidad'] > p['stock_maximo']]

        self._productos_filtrados = prods
        self._poblar_tabla(prods)

    def _limpiar_filtros(self):
        self.e_buscar.delete(0, tk.END)
        self.cb_cat.set('Todas')
        if hasattr(self, 'cb_prov_filtro'):
            self.cb_prov_filtro.set('Todos')
        if hasattr(self, 'cb_stock_estado'):
            self.cb_stock_estado.set('Todos')
        if hasattr(self, 'e_precio_min'):
            self.e_precio_min.delete(0, tk.END)
            self.e_precio_max.delete(0, tk.END)
        self._pagina_actual = 0
        self.cargar_productos()

    def _refrescar_todo(self):
        self.cargar_productos()

    # ── Cargar producto en formulario ─────────────────────────────────────────

    def cargar_producto_seleccionado(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        p = self.db.obtener_producto(self.tree.item(sel[0])['values'][0])
        if not p: return
        self.producto_seleccionado = p['id']

        def _set(w, val):
            if isinstance(w, tk.Text):
                w.delete('1.0', tk.END); w.insert('1.0', val or '')
            elif isinstance(w, ttk.Combobox):
                w.set(val or '')
            else:
                w.delete(0, tk.END); w.insert(0, str(val) if val is not None else '')

        _set(self.e_codigo,    p.get('codigo') or '')
        _set(self.e_nombre,    p['nombre'])

        # Actualizar label del panel de movimientos
        if hasattr(self, 'lbl_prod_mov'):
            cod = p.get('codigo') or ''
            cod_txt = f" [{cod}]" if cod else ""
            self.lbl_prod_mov.config(
                text=f"📦 Producto: {p['nombre']}{cod_txt}",
                foreground='#0F172A',
                font=('Segoe UI', 9, 'bold'))
        _set(self.e_desc,      p.get('descripcion', ''))
        _set(self.e_cantidad,  p['cantidad'])
        _set(self.e_stock_min, p.get('stock_minimo', 5))
        _set(self.e_stock_max, p.get('stock_maximo') or '')
        _set(self.e_precio_compra, p.get('precio_compra') or '')
        _set(self.e_precio,         p['precio_unitario'])
        self.e_unidad.set(p.get('unidad_medida') or 'Unidad')
        self.e_proveedor.set(p.get('proveedor', '') or '')
        self._refrescar_cats()
        categoria_actual = (p.get('categoria') or '').strip()
        valores_cat = list(self.e_categoria.cget('values')) if hasattr(self, 'e_categoria') else []
        if categoria_actual and categoria_actual not in valores_cat:
            self.e_categoria['values'] = tuple(valores_cat + [categoria_actual])
        self.e_categoria.set(categoria_actual)

        # Cargar campos opcionales
        for c in getattr(self, '_campos_opcionales_activos', []):
            w = getattr(self, f"e_opt_{c['key']}", None)
            if w:
                _set(w, p.get(c['key']) or '')

    def _datos_formulario(self):
        def _leer_entero(valor, etiqueta, default=None):
            if not valor:
                if default is not None:
                    return default
                raise ValueError(f"{etiqueta} es obligatorio.")
            try:
                return int(float(valor))
            except ValueError as exc:
                raise ValueError(f"{etiqueta} debe ser un numero entero.") from exc

        def _leer_decimal(valor, etiqueta, default=None):
            if not valor:
                if default is not None:
                    return default
                raise ValueError(f"{etiqueta} es obligatorio.")
            try:
                return float(valor)
            except ValueError as exc:
                raise ValueError(f"{etiqueta} debe ser un numero valido.") from exc

        nombre    = self.e_nombre.get().strip()
        desc      = self.e_desc.get('1.0', tk.END).strip()
        proveedor = self.e_proveedor.get().strip()
        categoria = self.e_categoria.get().strip()
        codigo    = self.e_codigo.get().strip()
        unidad    = self.e_unidad.get().strip()

        if not nombre:
            raise ValueError("El nombre del producto es requerido.")
        if not codigo:
            raise ValueError("El código / SKU es obligatorio.")
        if not proveedor:
            raise ValueError("El proveedor es obligatorio.\nSeleccione uno del listado.")
        if not categoria:
            raise ValueError("La categoría es obligatoria.")
        if not unidad:
            raise ValueError("La unidad de medida es obligatoria.")

        cantidad  = _leer_entero(self.e_cantidad.get().strip(), "La cantidad")
        precio_compra_raw = self.e_precio_compra.get().strip()
        precio_compra = _leer_decimal(precio_compra_raw, "El precio de compra", default=None)
        precio    = _leer_decimal(self.e_precio.get().strip(), "El precio de venta")
        stock_min = _leer_entero(self.e_stock_min.get().strip(), "El stock minimo")
        stock_max_raw = self.e_stock_max.get().strip()
        stock_max = _leer_entero(stock_max_raw, "El stock maximo")

        if precio_compra is not None and precio_compra < 0:
            raise ValueError("El precio de compra no puede ser negativo.")
        if precio < 0 or cantidad < 0 or stock_min < 0:
            raise ValueError("Cantidad, Precio y Stock Mínimo no pueden ser negativos.")
        if stock_max is not None and stock_max < stock_min:
            raise ValueError("El stock máximo no puede ser menor al stock mínimo.")

        id_proveedor = self._proveedores_map.get(proveedor)

        # Recoger valores de campos opcionales activos
        campos_opt = {}
        for c in getattr(self, '_campos_opcionales_activos', []):
            w = getattr(self, f"e_opt_{c['key']}", None)
            if w:
                campos_opt[c['key']] = w.get().strip() or None

        return {
            'nombre': nombre,
            'descripcion': desc,
            'cantidad': cantidad,
            'precio_unitario': precio,
            'proveedor': proveedor,
            'categoria': categoria,
            'stock_minimo': stock_min,
            'id_proveedor': id_proveedor,
            'codigo': codigo,
            'unidad_medida': unidad,
            'stock_maximo': stock_max,
            'precio_compra': precio_compra,
            'extras': campos_opt,
        }

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def crear_producto(self):
        try:
            datos = self._datos_formulario(); n = datos['nombre']
            ok, msg = self.db.crear_producto(**datos)
            if ok:
                self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                      'Crear producto', f'Nombre: {n}', n)
                messagebox.showinfo("✅ Éxito", f"Producto creado:\n{n}")
                self.limpiar_campos(); self.cargar_productos()
                self.verificar_alertas_stock(silencioso=True)
            else:
                messagebox.showerror("❌ Error", msg)
        except ValueError as e:
            messagebox.showwarning("⚠️ Validación", str(e))

    def actualizar_producto(self):
        if not self.producto_seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un producto (doble clic)."); return
        if not messagebox.askyesno("Confirmar", "¿Actualizar este producto?"):
            return
        try:
            datos = self._datos_formulario(); n = datos['nombre']; p = datos['precio_unitario']
            if not messagebox.askyesno("🔒 Confirmar",
                                       f"¿Guardar cambios en '{n}'?\nEsta acción no se puede deshacer."):
                return
            # Registrar cambio de precio si hubo
            prod_actual = self.db.obtener_producto(self.producto_seleccionado)
            if prod_actual and float(prod_actual['precio_unitario']) != p:
                self.db.registrar_cambio_precio(
                    self.producto_seleccionado,
                    float(prod_actual['precio_unitario']), p,
                    self.usuario['id'], self.usuario['username'])

            ok, msg = self.db.actualizar_producto(self.producto_seleccionado, **datos)
            if ok:
                self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                      'Actualizar producto', f'Nombre: {n}', n)
                messagebox.showinfo("✅ Éxito", msg)
                self.limpiar_campos(); self.cargar_productos()
            else:
                messagebox.showerror("❌ Error", msg)
        except ValueError as e:
            messagebox.showwarning("⚠️ Validación", str(e))

    def inhabilitar_producto(self):
        if not self.producto_seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un producto."); return
        nombre = self.e_nombre.get().strip() or f"ID {self.producto_seleccionado}"
        if not messagebox.askyesno("🚫 Inhabilitar",
                                   f"¿Inhabilitar '{nombre}'?\n\n"
                                   "Solo se puede inhabilitar si el stock es 0.\n"
                                   "Podrá reactivarlo desde 'Productos Inhabilitados'."):
            return
        ok, msg = self.db.inhabilitar_producto(self.producto_seleccionado)
        if ok:
            self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                  'Inhabilitar producto', f'ID: {self.producto_seleccionado}', nombre)
            messagebox.showinfo("✅", msg)
            self.limpiar_campos(); self.cargar_productos()
        else:
            messagebox.showerror("❌ No se puede inhabilitar", msg)

    def limpiar_campos(self):
        for attr in ('e_codigo', 'e_nombre', 'e_cantidad', 'e_precio_compra', 'e_precio',
                     'e_stock_min', 'e_stock_max'):
            try: getattr(self, attr).delete(0, tk.END)
            except Exception: pass
        try: self.e_desc.delete('1.0', tk.END)
        except Exception: pass
        try: self.e_proveedor.set('')
        except Exception: pass
        try: self.e_categoria.set('')
        except Exception: pass
        try: self.e_unidad.set('')
        except Exception: pass
        for c in getattr(self, '_campos_opcionales_activos', []):
            try: getattr(self, f"e_opt_{c['key']}").delete(0, tk.END)
            except Exception: pass
        self.producto_seleccionado = None
        if hasattr(self, 'lbl_prod_mov'):
            self.lbl_prod_mov.config(
                text="Producto: - (seleccione uno de la tabla)",
                foreground='#64748B',
                font=('Segoe UI', 9, 'italic'))
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    # ── Ventanas ──────────────────────────────────────────────────────────────

    def ver_productos_inactivos(self):
        inactivos = self.db.obtener_productos_inactivos()
        win = tk.Toplevel(self.root)
        win.title("🔄 Productos Inhabilitados")
        win.configure(bg=self.C['bg']); win.grab_set()
        configurar_ventana(win, width=860, height=560, min_width=760, min_height=500)

        ttk.Label(win, text=f"🔄 Productos Inhabilitados ({len(inactivos)})",
                  style='Header.TLabel').pack(pady=10, padx=12)
        ttk.Label(win, text="Seleccione un producto y haga clic en 'Habilitar' para reactivarlo.",
                  foreground=self.C['muted']).pack()

        frm = ttk.Frame(win); frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 0))
        sb = ttk.Scrollbar(frm); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('ID', 'Nombre', 'Categoría', 'Proveedor', 'Precio')
        tree = ttk.Treeview(frm, columns=cols, show='headings', yscrollcommand=sb.set)
        sb.config(command=tree.yview)
        for c, w in zip(cols, (50, 220, 120, 160, 100)):
            tree.heading(c, text=c); tree.column(c, width=w)
        for p in inactivos:
            tree.insert('', tk.END, values=(
                p['id'], p['nombre'], p.get('categoria') or '',
                p.get('proveedor') or 'N/A', f"${float(p['precio_unitario']):.2f}"))
        tree.pack(fill=tk.BOTH, expand=True)
        tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(tree)

        def habilitar():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("⚠️", "Seleccione un producto.", parent=win); return
            id_prod = tree.item(sel[0])['values'][0]
            nombre  = tree.item(sel[0])['values'][1]
            if not messagebox.askyesno("✅ Habilitar", f"¿Reactivar '{nombre}'?", parent=win): return
            ok, msg = self.db.habilitar_producto(id_prod)
            if ok:
                self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                      'Habilitar producto', f'ID: {id_prod}', nombre)
                messagebox.showinfo("✅", msg, parent=win)
                tree.delete(sel[0]); self.cargar_productos()
            else:
                messagebox.showerror("❌ Error", msg, parent=win)

        ttk.Button(win, text="✅ Habilitar Producto Seleccionado", command=habilitar).pack(pady=10)

    def ver_productos_criticos(self):
        criticos = self.db.obtener_productos_criticos()
        win = tk.Toplevel(self.root)
        win.title("🚨 Productos con Stock Crítico")
        win.configure(bg=self.C['bg']); win.grab_set()
        configurar_ventana(win, width=840, height=540, min_width=740, min_height=480)

        ttk.Label(win, text=f"🚨 {len(criticos)} producto(s) en nivel crítico",
                  style='Header.TLabel').pack(pady=10, padx=12)
        frm = ttk.Frame(win); frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        sb = ttk.Scrollbar(frm); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('Nombre', 'Stock Actual', 'Stock Mínimo', 'Diferencia', 'Proveedor')
        tree = ttk.Treeview(frm, columns=cols, show='headings', yscrollcommand=sb.set)
        sb.config(command=tree.yview)
        for c in cols:
            tree.heading(c, text=c); tree.column(c, width=110 if c != 'Nombre' else 200)
        tree.tag_configure('cero', background='#FEE2E2')
        tree.tag_configure('bajo', background='#FEF9C3')
        for p in criticos:
            tag = 'cero' if p['cantidad'] <= 0 else 'bajo'
            tree.insert('', tk.END, tags=(tag,), values=(
                p['nombre'], p['cantidad'], p['stock_minimo'],
                p['cantidad'] - p['stock_minimo'], p.get('proveedor') or 'N/A'))
        tree.pack(fill=tk.BOTH, expand=True)
        tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(tree)

    def ver_historial_producto(self):
        if not self.producto_seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un producto primero."); return
        hist   = self.db.obtener_historial_producto(self.producto_seleccionado)
        nombre = self.e_nombre.get() or f"ID {self.producto_seleccionado}"
        win = tk.Toplevel(self.root)
        win.title(f"📋 Historial — {nombre}")
        win.configure(bg=self.C['bg']); win.grab_set()
        configurar_ventana(win, width=920, height=620, min_width=820, min_height=520)

        ttk.Label(win, text=f"📋 Historial de movimientos: {nombre}",
                  style='Header.TLabel').pack(pady=10, padx=12)
        frm = ttk.Frame(win); frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        sb = ttk.Scrollbar(frm); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('ID', 'Tipo', 'Cantidad', 'Fecha', 'Usuario', 'Nota')
        tree = ttk.Treeview(frm, columns=cols, show='headings', yscrollcommand=sb.set)
        sb.config(command=tree.yview)
        anchos = {'ID': 45, 'Tipo': 80, 'Cantidad': 75, 'Fecha': 150, 'Usuario': 110, 'Nota': 200}
        for c in cols:
            tree.heading(c, text=c); tree.column(c, width=anchos[c])
        tree.tag_configure('entrada', foreground='#065F46')
        tree.tag_configure('salida',  foreground='#991B1B')
        for m in hist:
            tag = 'entrada' if 'entrada' in str(m.get('tipo_movimiento', '')).lower() else 'salida'
            tree.insert('', tk.END, tags=(tag,), values=(
                m['id'], m['tipo_movimiento'], m['cantidad'],
                m['fecha'].strftime('%d/%m/%Y %H:%M') if m['fecha'] else '',
                m.get('usuario', 'Sistema'), m.get('descripcion', '') or ''))
        tree.pack(fill=tk.BOTH, expand=True)
        tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(tree)
        ttk.Label(win, text=f"Total de movimientos: {len(hist)}",
                  foreground=self.C['muted']).pack(pady=4)

    def ver_historial_precios(self):
        """Muestra el historial de cambios de precio del producto seleccionado."""
        if not self.producto_seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un producto primero."); return
        hist   = self.db.obtener_historial_precios(self.producto_seleccionado)
        nombre = self.e_nombre.get() or f"ID {self.producto_seleccionado}"

        win = tk.Toplevel(self.root)
        win.title(f"💰 Historial de precios — {nombre}")
        win.configure(bg=self.C['bg']); win.grab_set()
        configurar_ventana(win, width=820, height=520, min_width=720, min_height=460)

        ttk.Label(win, text=f"💰 Historial de precios: {nombre}",
                  style='Header.TLabel').pack(pady=10, padx=12)
        ttk.Label(win, text="Solo se registran cambios al actualizar el producto.",
                  foreground=self.C['muted']).pack(padx=12)

        frm = ttk.Frame(win); frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))
        sb = ttk.Scrollbar(frm); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('Precio Anterior', 'Precio Nuevo', 'Diferencia', 'Usuario', 'Fecha')
        tree = ttk.Treeview(frm, columns=cols, show='headings', yscrollcommand=sb.set)
        sb.config(command=tree.yview)
        anchos = {'Precio Anterior': 120, 'Precio Nuevo': 120,
                  'Diferencia': 100, 'Usuario': 110, 'Fecha': 140}
        for c in cols:
            tree.heading(c, text=c); tree.column(c, width=anchos[c], anchor='center')
        tree.tag_configure('subio',  foreground='#065F46')
        tree.tag_configure('bajo',   foreground='#991B1B')
        tree.tag_configure('igual',  foreground='#64748B')

        if not hist:
            ttk.Label(win, text="No hay cambios de precio registrados para este producto.",
                      foreground=self.C['muted']).pack(pady=20)
        else:
            for h in hist:
                diff = float(h.get('diferencia', 0))
                tag  = 'subio' if diff > 0 else ('bajo' if diff < 0 else 'igual')
                signo = '+' if diff > 0 else ''
                fecha = h['fecha'].strftime('%d/%m/%Y %H:%M') if h.get('fecha') else ''
                tree.insert('', tk.END, tags=(tag,), values=(
                    f"${float(h['precio_anterior']):.2f}",
                    f"${float(h['precio_nuevo']):.2f}",
                    f"{signo}${abs(diff):.2f}",
                    h.get('username', 'Sistema'),
                    fecha))
            tree.pack(fill=tk.BOTH, expand=True)
        tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(tree)

    # ── Movimiento ────────────────────────────────────────────────────────────

    def registrar_movimiento(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("⚠️", "Seleccione un producto de la tabla."); return
        producto_vals = self.tree.item(sel[0])['values']
        id_prod  = producto_vals[0]
        nombre_prod = producto_vals[2]
        tipo_raw = self.cb_tipo_mov.get()
        if not tipo_raw:
            messagebox.showwarning("⚠️", "Seleccione tipo de movimiento."); return
        tipo = tipo_raw.split()[-1]
        try:
            cant = int(self.e_cant_mov.get().strip())
            if cant <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("⚠️", "Ingrese una cantidad entera mayor a 0."); return

        nota = self.e_nota_mov.get().strip()
        autorizado = pedir_confirmacion_password(
            self.root,
            self.db,
            self.usuario['id'],
            "Confirmar movimiento",
            f"Confirme su contraseña para registrar una {tipo.lower()} de "
            f"{cant} unidad(es) para '{nombre_prod}'.",
            bg=self.C['bg'],
            title_fg=self.C['text'],
            prompt_text='Contraseña del usuario:',
            button_style='Warn.TButton',
            confirm_text='Confirmar',
            geometry='390x220',
            wraplength=340)
        if not autorizado:
            return

        ok, msg = self.db.registrar_movimiento(id_prod, tipo, cant, nota, self.usuario['id'])
        if ok:
            self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                  f'Movimiento {tipo}', f'Cantidad: {cant}',
                                  str(nombre_prod))
            self.e_cant_mov.delete(0, tk.END)
            self.e_nota_mov.delete(0, tk.END)
            self.cb_tipo_mov.set('')
            self.cargar_productos()
            self.verificar_alertas_stock(silencioso=True)
        else:
            messagebox.showwarning("⚠️ Stock insuficiente", msg)

    # ── Stats y alertas ───────────────────────────────────────────────────────

    def actualizar_estadisticas(self):
        s = self.db.obtener_estadisticas()
        self.lbl_prod.config(    text=f"  📊 Productos: {s.get('total_productos', 0)}")
        self.lbl_stock.config(   text=f"  📦 Stock Total: {s.get('stock_total', 0)}")
        self.lbl_valor.config(   text=f"  💰 Valor: ${s.get('valor_total', 0):.2f}")
        critico = s.get('bajo_stock', 0)
        self.lbl_critico.config( text=f"  🚨 Críticos: {critico}",
                                 fg=self.C['danger'] if critico > 0 else self.C['muted'])
        self.lbl_provs.config(   text=f"  🏭 Proveedores: {s.get('total_proveedores', 0)}")

    def verificar_alertas_stock(self, silencioso=False):
        criticos = self.db.obtener_productos_criticos()
        if not criticos: return
        if not silencioso:
            msg = "\n".join(
                f"• {p['nombre']}  (stock: {p['cantidad']} / mín: {p['stock_minimo']})"
                for p in criticos[:10])
            if len(criticos) > 10:
                msg += f"\n... y {len(criticos)-10} más"
            messagebox.showwarning("🚨 Alerta de Stock Bajo",
                                   f"{len(criticos)} producto(s) en nivel crítico:\n\n{msg}")
        else:
            self.actualizar_estadisticas()

    def abrir_ingreso_masivo(self):
        from modulos.ingreso_masivo import IngresoMasivoWindow
        def _al_cerrar():
            self.cargar_productos()
        IngresoMasivoWindow(self.root, self.db, self.C, self.usuario, _al_cerrar)
