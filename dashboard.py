import tkinter as tk
from tkinter import ttk, messagebox
import os, sys, subprocess
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from gui.estilos import aplicar_estilos, PALETAS
from gui.menu import construir_topbar, construir_sidebar
from gui.inventario import InventarioMixin
from gui.reportes_ui import ReportesUIMixin
from gui.ui_helpers import bloquear_columnas, configurar_ventana

AUTO_REFRESH_MS = 30000


class InventoryManagementApp(InventarioMixin, ReportesUIMixin):

    def __init__(self, root, db, usuario_actual):
        self.root    = root
        self.db      = db
        self.usuario = usuario_actual
        self.producto_seleccionado = None
        self._pagina_activa     = 'dashboard'
        self._sidebar_btns      = {}
        self._sidebar_colapsado = False
        self._acc_open          = None
        self._auto_refresh_id   = None
        self._kpi_valores_prev  = {}
        self._kpi_labels        = {}
        self._dash_frame        = None

        self._empresa_nombre = self.db.get_empresa_nombre()
        self._empresa_logo   = self.db.get_empresa_logo()
        paleta_guardada      = self.db.get_config('paleta', 'corporate')
        self._paleta_actual  = paleta_guardada if paleta_guardada in PALETAS else 'corporate'

        self.C = aplicar_estilos(root, self._paleta_actual)
        self._titulo_pagina = tk.StringVar(value="🏠  Inicio")

        self.root.title(
            f"Inventoryx  —  {self._empresa_nombre}  —  "
            f"{usuario_actual['nombre_completo']} ({usuario_actual['rol']})")
        configurar_ventana(
            self.root,
            size='main',
            min_width=1100,
            min_height=700,
            start_maximized=True,
        )

        self._construir_ui()
        self.cargar_productos()
        self.root.after(1500, self.verificar_alertas_stock)

        self._inactividad_id = None
        self._resetear_inactividad()
        for ev in ('<Motion>', '<KeyPress>', '<ButtonPress>'):
            self.root.bind_all(ev, lambda e: self._resetear_inactividad())

        self.root.bind_all('<F5>',     lambda e: self.cargar_productos())
        self.root.bind_all('<Escape>', lambda e: self.limpiar_campos())
        # La X no cierra — solo el botón de cerrar sesión del sidebar
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

    def perm(self, p):
        return self.db.tiene_permiso(self.usuario, p)

    # ── Paleta ────────────────────────────────────────────────────────────────

    def _cambiar_paleta(self, paleta_key):
        if paleta_key == self._paleta_actual:
            return
        self._paleta_actual = paleta_key
        self.db.set_config('paleta', paleta_key)
        self._cancelar_auto_refresh()
        for w in self.root.winfo_children():
            w.destroy()
        self.C = aplicar_estilos(self.root, paleta_key)
        self._sidebar_btns  = {}
        self._acc_open      = None
        self._titulo_pagina = tk.StringVar(value="🏠  Inicio")
        self._dash_frame    = None
        self._kpi_labels    = {}
        self._construir_ui()
        self.cargar_productos()
        self._mostrar_pagina(self._pagina_activa)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _toggle_sidebar(self):
        self._sidebar_colapsado = not self._sidebar_colapsado
        if hasattr(self, '_sidebar_outer') and self._sidebar_outer.winfo_exists():
            self._sidebar_outer.destroy()
        construir_sidebar(self._container, self, self.C,
                          self._empresa_nombre, self._empresa_logo,
                          colapsado=self._sidebar_colapsado)
        self._area.pack_forget()
        self._area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._actualizar_highlight_sidebar()

    def _actualizar_highlight_sidebar(self):
        for key, btn in self._sidebar_btns.items():
            try:
                btn.config(
                    bg=self.C['primary'] if key == self._pagina_activa else self.C['sidebar_bg'],
                    fg='white')
            except Exception:
                pass

    # ── UI ────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        construir_topbar(self.root, self._titulo_pagina, self.C, self)

        self._container = tk.Frame(self.root, bg=self.C['bg'])
        self._container.pack(fill=tk.BOTH, expand=True)

        construir_sidebar(self._container, self, self.C,
                          self._empresa_nombre, self._empresa_logo,
                          colapsado=self._sidebar_colapsado)

        self._area = tk.Frame(self._container, bg=self.C['bg'])
        self._area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._pagina_dashboard  = tk.Frame(self._area, bg=self.C['bg'])
        self._pagina_inventario = tk.Frame(self._area, bg=self.C['bg'])

        main = ttk.Frame(self._pagina_inventario)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))

        frm_izq = tk.Frame(main, bg=self.C['bg'], width=280)
        frm_izq.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        frm_izq.pack_propagate(False)
        self._construir_formulario(frm_izq)

        frm_der = ttk.Frame(main)
        frm_der.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._construir_busqueda(frm_der)
        self._construir_tabla(frm_der)
        self._construir_movimientos(frm_der)
        self._construir_stats(frm_der)

        self._mostrar_pagina('dashboard')

    # ── Navegación ────────────────────────────────────────────────────────────

    def _mostrar_pagina(self, pagina):
        self._cancelar_auto_refresh()
        self._pagina_dashboard.pack_forget()
        self._pagina_inventario.pack_forget()
        self._pagina_activa = pagina

        titulos = {'dashboard': '🏠  Inicio', 'inventario': '📦  Inventario'}
        self._titulo_pagina.set(titulos.get(pagina, pagina))

        if pagina == 'dashboard':
            self._pagina_dashboard.pack(fill=tk.BOTH, expand=True)
            self._refrescar_dashboard()
            self._iniciar_auto_refresh()
        elif pagina == 'inventario':
            self._pagina_inventario.pack(fill=tk.BOTH, expand=True)

        self._actualizar_highlight_sidebar()

    # ── Auto-refresh ──────────────────────────────────────────────────────────

    def _iniciar_auto_refresh(self):
        self._cancelar_auto_refresh()
        self._auto_refresh_id = self.root.after(AUTO_REFRESH_MS, self._auto_refresh_tick)

    def _cancelar_auto_refresh(self):
        if self._auto_refresh_id:
            try: self.root.after_cancel(self._auto_refresh_id)
            except Exception: pass
            self._auto_refresh_id = None

    def _auto_refresh_tick(self):
        if self._pagina_activa != 'dashboard':
            return
        try:
            self._actualizar_kpis_silencioso()
        except Exception:
            pass
        self._auto_refresh_id = self.root.after(AUTO_REFRESH_MS, self._auto_refresh_tick)

    def _actualizar_kpis_silencioso(self):
        if not self._kpi_labels:
            return
        stats = self.db.obtener_estadisticas()
        mapa  = {
            'total_productos':   stats.get('total_productos', 0),
            'stock_total':       stats.get('stock_total', 0),
            'valor_total':       stats.get('valor_total', 0.0),
            'bajo_stock':        stats.get('bajo_stock', 0),
            'total_proveedores': stats.get('total_proveedores', 0),
        }
        for key, (lbl_val, _, color, _bg) in self._kpi_labels.items():
            nuevo = mapa.get(key, 0)
            prev  = self._kpi_valores_prev.get(key, nuevo)
            if nuevo != prev:
                self._animar_kpi(lbl_val, prev, nuevo, color, key)
            self._kpi_valores_prev[key] = nuevo

    def _animar_kpi(self, label, desde, hasta, color, key, pasos=12, paso=0):
        try:
            if not label.winfo_exists(): return
        except Exception: return
        if paso >= pasos:
            v = f"${hasta:.2f}" if key == 'valor_total' else str(int(hasta))
            try: label.config(text=v, fg=color)
            except Exception: pass
            return
        t  = (paso + 1) / pasos
        t2 = 1 - (1 - t) ** 2
        try:
            act = desde + (hasta - desde) * t2
        except TypeError:
            act = hasta
        v = f"${act:.2f}" if key == 'valor_total' else str(int(act))
        try: label.config(text=v)
        except Exception: return
        self.root.after(30, lambda: self._animar_kpi(label, desde, hasta, color, key, pasos, paso+1))

    # ── Toast ─────────────────────────────────────────────────────────────────

    def _toast(self, mensaje, tipo='info', duracion=3000):
        colores = {
            'info':    (self.C['primary'],   self.C['surface']),
            'success': (self.C['secondary'], self.C['surface']),
            'warning': (self.C['warning'],   self.C['surface']),
            'error':   (self.C['danger'],    self.C['surface']),
        }
        fg, bg = colores.get(tipo, colores['info'])
        toast  = tk.Toplevel(self.root)
        toast.wm_overrideredirect(True)
        toast.attributes('-topmost', True)
        toast.configure(bg=bg)
        self.root.update_idletasks()
        rw = self.root.winfo_width(); rh = self.root.winfo_height()
        rx = self.root.winfo_rootx(); ry = self.root.winfo_rooty()
        tk.Label(toast, text=mensaje, bg=bg, fg=fg,
                 font=("Segoe UI", 9, "bold"),
                 padx=16, pady=8, relief='flat').pack()
        toast.update_idletasks()
        tw = toast.winfo_width(); th = toast.winfo_height()
        toast.wm_geometry(f"+{rx+rw-tw-20}+{ry+rh-th-40}")
        toast.after(duracion, lambda: toast.destroy() if toast.winfo_exists() else None)

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def _refrescar_dashboard(self):
        if self._dash_frame:
            try: self._dash_frame.destroy()
            except Exception: pass
            plt.close('all')

        self._kpi_labels = {}
        self._dash_frame = tk.Frame(self._pagina_dashboard, bg=self.C['bg'])
        self._dash_frame.pack(fill=tk.BOTH, expand=True)
        C = self.C

        # Bienvenida
        hdr = tk.Frame(self._dash_frame, bg=C['header_bg'], height=46)
        hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr, text=f"  👋  Bienvenido, {self.usuario['nombre_completo']}",
                 font=("Segoe UI", 11, "bold"),
                 bg=C['header_bg'], fg='white').pack(side=tk.LEFT, padx=12)
        self._lbl_fecha = tk.Label(hdr,
                                   text=datetime.now().strftime("📅  %d/%m/%Y  %H:%M"),
                                   font=("Segoe UI", 9),
                                   bg=C['header_bg'], fg=C['muted'])
        self._lbl_fecha.pack(side=tk.RIGHT, padx=12)
        self._actualizar_reloj()

        # Body scroll
        body_outer = tk.Frame(self._dash_frame, bg=C['bg'])
        body_outer.pack(fill=tk.BOTH, expand=True)
        vsb = tk.Scrollbar(body_outer, orient='vertical')
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        body_cvs = tk.Canvas(body_outer, bg=C['bg'],
                             yscrollcommand=vsb.set, highlightthickness=0)
        body_cvs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=body_cvs.yview)
        body = tk.Frame(body_cvs, bg=C['bg'])
        win_id = body_cvs.create_window((0, 0), window=body, anchor='nw')
        body.bind('<Configure>', lambda e: body_cvs.configure(
            scrollregion=body_cvs.bbox('all')))
        body_cvs.bind('<Configure>',
                      lambda e: body_cvs.itemconfig(win_id, width=e.width))
        body_cvs.bind_all('<MouseWheel>',
                          lambda e: body_cvs.yview_scroll(int(-1*(e.delta/120)), "units"))

        # KPIs
        stats = self.db.obtener_estadisticas()
        kpi_defs = [
            ('total_productos',   "📦", "Productos",     C['primary'],   ),
            ('stock_total',       "📊", "Stock Total",   '#0F766E',      ),
            ('valor_total',       "💰", "Valor Total",   C['secondary'], ),
            ('bajo_stock',        "🚨", "Críticos",      C['danger'],    ),
            ('total_proveedores', "🏭", "Proveedores",   '#D97706',      ),
        ]

        frm_kpi = tk.Frame(body, bg=C['bg'])
        frm_kpi.pack(fill=tk.X, padx=12, pady=(10, 6))

        for col_i, (key, icon, titulo, color) in enumerate(kpi_defs):
            frm_kpi.columnconfigure(col_i, weight=1)
            raw = stats.get(key, 0)
            val_str = f"${raw:.2f}" if key == 'valor_total' else str(raw)

            card = tk.Frame(frm_kpi, bg=C['card_bg'],
                            highlightbackground=color, highlightthickness=1)
            card.grid(row=0, column=col_i, padx=4, pady=2, sticky='nsew')

            tk.Label(card, text=icon, font=("Segoe UI", 18),
                     bg=C['card_bg']).pack(pady=(10, 0))
            lbl_val = tk.Label(card, text=val_str,
                               font=("Segoe UI", 13, "bold"),
                               bg=C['card_bg'], fg=color)
            lbl_val.pack()
            tk.Label(card, text=titulo, font=("Segoe UI", 8),
                     bg=C['card_bg'], fg=C['muted']).pack(pady=(0, 8))
            tk.Frame(card, bg=color, height=3).pack(fill=tk.X, side=tk.BOTTOM)

            self._kpi_labels[key]      = (lbl_val, titulo, color, C['card_bg'])
            self._kpi_valores_prev[key] = raw

        # Fila inferior
        frm_bot = tk.Frame(body, bg=C['bg'])
        frm_bot.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 10))
        frm_bot.columnconfigure(0, weight=3)
        frm_bot.columnconfigure(1, weight=2)
        frm_bot.rowconfigure(0, weight=1)

        surf = C['surface']

        # Movimientos con buscador
        frm_movs = tk.LabelFrame(frm_bot, text="  🕒  Últimos Movimientos",
                                  font=("Segoe UI", 9, "bold"),
                                  bg=surf, fg=C['text'],
                                  relief='flat',
                                  highlightbackground=C['border'],
                                  highlightthickness=1)
        frm_movs.grid(row=0, column=0, sticky='nsew', padx=(0, 6))

        barra = tk.Frame(frm_movs, bg=surf)
        barra.pack(fill=tk.X, padx=4, pady=(4, 2))
        tk.Label(barra, text="🔍", bg=surf, fg=C['muted'],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        e_filtro = tk.Entry(barra, bg=surf, fg=C['text'],
                            insertbackground=C['text'],
                            font=("Segoe UI", 9), relief='flat',
                            highlightthickness=1,
                            highlightbackground=C['border'])
        e_filtro.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        sb = tk.Scrollbar(frm_movs)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('Producto', 'Tipo', 'Cant.', 'Fecha', 'Usuario')
        tree = ttk.Treeview(frm_movs, columns=cols, show='headings',
                             yscrollcommand=sb.set, height=9)
        sb.config(command=tree.yview)
        for c, w in zip(cols, (185, 75, 55, 130, 90)):
            tree.heading(c, text=c,
                         command=lambda _c=c: _ordenar_tree(tree, _c, False))
            tree.column(c, width=w,
                        anchor='center' if c != 'Producto' else 'w')
        tree.tag_configure('entrada', foreground=C['secondary'])
        tree.tag_configure('salida',  foreground=C['danger'])
        tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        bloquear_columnas(tree)

        self._movs_cache = self.db.buscar_movimientos()[:50]

        def _poblar(filtro=''):
            tree.delete(*tree.get_children())
            for m in self._movs_cache:
                prod = m.get('nombre_producto', '') or ''
                if filtro and filtro.lower() not in prod.lower():
                    continue
                tipo = str(m.get('tipo_movimiento', '')).lower()
                tag  = 'entrada' if 'entrada' in tipo else 'salida'
                fecha = m['fecha'].strftime('%d/%m %H:%M') if m.get('fecha') else ''
                tree.insert('', tk.END, tags=(tag,), values=(
                    prod[:28], m.get('tipo_movimiento', ''),
                    m.get('cantidad', 0), fecha,
                    m.get('usuario_nombre') or 'Sistema'))

        _poblar()
        e_filtro.bind('<KeyRelease>', lambda e: _poblar(e_filtro.get()))

        # Gráfico
        frm_chart = tk.LabelFrame(frm_bot, text="  📈  Actividad — 7 días",
                                   font=("Segoe UI", 9, "bold"),
                                   bg=surf, fg=C['text'],
                                   relief='flat',
                                   highlightbackground=C['border'],
                                   highlightthickness=1)
        frm_chart.grid(row=0, column=1, sticky='nsew')

        hoy    = datetime.now().date()
        inicio = hoy - timedelta(days=6)
        fechas = [inicio + timedelta(days=i) for i in range(7)]
        ents   = {d: 0 for d in fechas}
        sals   = {d: 0 for d in fechas}

        for m in self.db.obtener_movimientos():
            fd = m['fecha'].date() if m.get('fecha') else None
            if fd and fd in ents:
                t = (m.get('tipo_movimiento') or '').lower()
                v = int(m.get('cantidad') or 0)
                if 'entrada' in t: ents[fd] += v
                else:              sals[fd] += v

        is_dark = C['nombre'] != 'slate'
        pbg = surf
        abg = C['bg'] if not is_dark else C['card_bg']
        tc  = C['text']

        fig, ax = plt.subplots(figsize=(3.8, 2.8), facecolor=pbg)
        ax.set_facecolor(abg)
        x = range(len(fechas))
        ax.bar([i-.2 for i in x], [ents[d] for d in fechas],
               width=0.38, label='Entradas', color=C['secondary'], alpha=0.85)
        ax.bar([i+.2 for i in x], [sals[d] for d in fechas],
               width=0.38, label='Salidas',  color=C['danger'],    alpha=0.85)
        ax.set_xticks(list(x))
        ax.set_xticklabels([d.strftime('%d/%m') for d in fechas],
                           fontsize=7, color=tc)
        ax.tick_params(colors=tc, labelsize=7)
        for sp in ax.spines.values():
            sp.set_color(C['border'])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        hdls, _ = ax.get_legend_handles_labels()
        if hdls:
            ax.legend(fontsize=7, facecolor=pbg, labelcolor=tc, framealpha=0.5)
        ax.set_title('Entradas vs Salidas', fontsize=8,
                     fontweight='bold', color=tc, pad=4)
        fig.tight_layout(pad=0.6)
        cv = FigureCanvasTkAgg(fig, master=frm_chart)
        cv.draw()
        cv.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        plt.close(fig)

    def _actualizar_reloj(self):
        try:
            if hasattr(self, '_lbl_fecha') and self._lbl_fecha.winfo_exists():
                self._lbl_fecha.config(
                    text=datetime.now().strftime("📅  %d/%m/%Y  %H:%M"))
                self.root.after(60000, self._actualizar_reloj)
        except Exception:
            pass

    # ── Gráficos ventana ──────────────────────────────────────────────────────

    def abrir_graficos(self):
        self.abrir_centro_reportes(tab_inicial="graficos_dinamicos")
        return
        win = tk.Toplevel(self.root)
        win.title("📊 Visualización de Estadísticas")
        win.configure(bg=self.C['bg'])
        configurar_ventana(win, width=1120, height=740, min_width=980, min_height=640)
        ttk.Label(win, text="📊 Análisis y Visualización",
                  style='Header.TLabel').pack(pady=10, padx=12)
        nb    = ttk.Notebook(win)
        nb.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        prods = self.db.obtener_productos()
        pbg   = self.C['surface']
        abg   = self.C['bg']
        tc    = self.C['text']

        def tab_barras(titulo, etiquetas, valores, xlabel):
            p = ttk.Frame(nb); nb.add(p, text=titulo)
            fig, ax = plt.subplots(figsize=(8, 4), facecolor=pbg)
            ax.set_facecolor(abg)
            ax.barh(etiquetas[::-1], valores[::-1], color=self.C['secondary'])
            ax.set_title(titulo, fontsize=11, fontweight='bold', color=tc)
            ax.set_xlabel(xlabel, color=tc)
            ax.tick_params(colors=tc)
            fig.tight_layout()
            FigureCanvasTkAgg(fig, master=p).get_tk_widget().pack(
                fill=tk.BOTH, expand=True, padx=8, pady=8)

        top10 = sorted(prods, key=lambda x: x.get('cantidad', 0), reverse=True)[:10]
        tab_barras("Top 10 Stock",
                   [p['nombre'] for p in top10],
                   [p['cantidad'] for p in top10], "Cantidad")

        top10v = sorted(prods,
                        key=lambda x: float(x.get('cantidad', 0)) * float(x.get('precio_unitario', 0)),
                        reverse=True)[:10]
        tab_barras("Top 10 Valor ($)",
                   [p['nombre'] for p in top10v],
                   [float(p['cantidad'])*float(p['precio_unitario']) for p in top10v], "Valor $")

        p2 = ttk.Frame(nb); nb.add(p2, text="Por Categoria")
        stk = {}
        for p in prods:
            cat = p.get('categoria') or 'Sin categoria'
            stk[cat] = stk.get(cat, 0) + (p.get('cantidad') or 0)
        fig2, ax2 = plt.subplots(figsize=(6, 5), facecolor=pbg)
        if any(stk.values()):
            ax2.pie(list(stk.values()), labels=list(stk.keys()),
                    autopct='%1.1f%%', startangle=140)
            ax2.set_title("Stock por categoria", fontsize=11,
                          fontweight='bold', color=tc)
        fig2.tight_layout()
        FigureCanvasTkAgg(fig2, master=p2).get_tk_widget().pack(
            fill=tk.BOTH, expand=True, padx=8, pady=8)

        p3    = ttk.Frame(nb); nb.add(p3, text="Movimientos 30 dias")
        movs  = self.db.obtener_movimientos()
        hoy   = datetime.now().date()
        ini30 = hoy - timedelta(days=29)
        neto  = {}
        for m in movs:
            f = m.get('fecha')
            if not f: continue
            fd = f.date()
            if not (ini30 <= fd <= hoy): continue
            cv = int(m.get('cantidad') or 0)
            t  = (m.get('tipo_movimiento') or '').lower()
            neto[fd] = neto.get(fd, 0) + (cv if 'entrada' in t else -cv)
        fechas30 = [ini30 + timedelta(days=i) for i in range(30)]
        vals30   = [neto.get(d, 0) for d in fechas30]
        fig3, ax3 = plt.subplots(figsize=(9, 3.5), facecolor=pbg)
        ax3.set_facecolor(abg)
        ax3.bar(fechas30, vals30,
                color=[self.C['secondary'] if v >= 0 else self.C['danger'] for v in vals30])
        ax3.set_title('Movimiento neto diario (ultimos 30 dias)',
                      fontsize=11, fontweight='bold', color=tc)
        ax3.tick_params(colors=tc)
        ax3.grid(axis='y', alpha=0.2, color=tc)
        fig3.autofmt_xdate(rotation=45)
        fig3.tight_layout()
        FigureCanvasTkAgg(fig3, master=p3).get_tk_widget().pack(
            fill=tk.BOTH, expand=True, padx=8, pady=8)

    # ── Módulos ───────────────────────────────────────────────────────────────

    def abrir_campos_opcionales(self):
        from modulos.campos_opcionales import CamposOpcionalesWindow
        win = CamposOpcionalesWindow(self.root, self.db, self.C, self.usuario)
        # Cuando se cierra, reconstruir la página de inventario para que
        # aparezcan/desaparezcan los campos opcionales inmediatamente
        def _al_cerrar():
            try:
                self._reconstruir_inventario()
            except Exception:
                pass
        win.win.bind('<Destroy>', lambda e: _al_cerrar())

    def _reconstruir_inventario(self):
        """Destruye y reconstruye el frame de inventario con los campos actualizados."""
        try:
            self._pagina_inventario.destroy()
        except Exception:
            pass
        self._pagina_inventario = tk.Frame(self._area, bg=self.C['bg'])
        main = ttk.Frame(self._pagina_inventario)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))
        frm_izq = tk.Frame(main, bg=self.C['bg'], width=280)
        frm_izq.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        frm_izq.pack_propagate(False)
        self._construir_formulario(frm_izq)
        frm_der = ttk.Frame(main)
        frm_der.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._construir_busqueda(frm_der)
        self._construir_tabla(frm_der)
        self._construir_movimientos(frm_der)
        self._construir_stats(frm_der)
        if self._pagina_activa == 'inventario':
            self._pagina_inventario.pack(fill=tk.BOTH, expand=True)
        self.cargar_productos()

    def abrir_config_sistema(self):
        win = tk.Toplevel(self.root)
        win.title("⚙️ Configuración del Sistema")
        win.configure(bg=self.C['bg'])
        win.grab_set()
        configurar_ventana(
            win,
            width=620,
            height=500,
            min_width=620,
            min_height=500,
            resizable=(False, False),
        )

        ttk.Label(win, text="⚙️ Configuración del Sistema",
                  style='Header.TLabel').pack(pady=(18, 2), padx=20, anchor='w')
        ttk.Label(win, text="Los cambios aplican al reiniciar sesión y en los reportes PDF.",
                  foreground=self.C['muted']).pack(padx=20, anchor='w')

        frm = ttk.Frame(win)
        frm.pack(padx=20, pady=14, fill=tk.X)
        frm.columnconfigure(1, weight=1)

        # Nombre
        ttk.Label(frm, text="Nombre empresa:").grid(
            row=0, column=0, sticky='w', pady=6, padx=(0, 12))
        e_nombre = ttk.Entry(frm, width=32)
        e_nombre.insert(0, self.db.get_empresa_nombre())
        e_nombre.grid(row=0, column=1, sticky='ew', pady=6)

        # Dirección
        ttk.Label(frm, text="Dirección:").grid(
            row=1, column=0, sticky='w', pady=6, padx=(0, 12))
        e_dir = ttk.Entry(frm, width=32)
        e_dir.insert(0, self.db.get_config('empresa_direccion', ''))
        e_dir.grid(row=1, column=1, sticky='ew', pady=6)

        # Teléfono
        ttk.Label(frm, text="Teléfono:").grid(
            row=2, column=0, sticky='w', pady=6, padx=(0, 12))
        e_tel = ttk.Entry(frm, width=32)
        e_tel.insert(0, self.db.get_config('empresa_telefono', ''))
        e_tel.grid(row=2, column=1, sticky='ew', pady=6)

        # Logo
        ttk.Label(frm, text="Logo:").grid(
            row=3, column=0, sticky='w', pady=6, padx=(0, 12))
        frm_logo = ttk.Frame(frm)
        frm_logo.grid(row=3, column=1, sticky='ew')
        e_logo = ttk.Entry(frm_logo, width=22)
        e_logo.insert(0, self.db.get_empresa_logo())
        e_logo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        import shutil
        from tkinter import filedialog

        def sel():
            ruta = filedialog.askopenfilename(
                title="Seleccionar logo",
                filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp"), ("Todos", "*.*")])
            if not ruta: return
            dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logo.png')
            try:
                shutil.copy2(ruta, dest)
                e_logo.delete(0, tk.END); e_logo.insert(0, 'logo.png')
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=win)

        ttk.Button(frm_logo, text="📁", command=sel, width=3
                   ).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(frm, text="(El logo y datos aparecen en el encabezado de los PDFs)",
                  font=('Segoe UI', 8), foreground=self.C['muted']
                  ).grid(row=4, column=0, columnspan=2, sticky='w', pady=(2, 0))

        msg = tk.Label(win, text='', font=('Segoe UI', 9),
                       bg=self.C['bg'], fg=self.C['secondary'])
        msg.pack(pady=4)

        def guardar():
            nombre = e_nombre.get().strip()
            if not nombre:
                msg.config(text="El nombre no puede estar vacío.",
                           fg=self.C['danger']); return
            self.db.set_empresa_nombre(nombre)
            self.db.set_empresa_logo(e_logo.get().strip())
            self.db.set_config('empresa_direccion', e_dir.get().strip())
            self.db.set_config('empresa_telefono',  e_tel.get().strip())
            self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                  'Config sistema', f'Empresa: {nombre}')
            msg.config(text="✅ Guardado. Los reportes ya incluirán el membrete.",
                       fg=self.C['secondary'])
            self._toast("✅ Configuración guardada", 'success')

        ttk.Button(win, text="💾 Guardar", command=guardar,
                   style='Create.TButton').pack(pady=(0, 8))

        tk.Frame(win, bg=self.C['border'], height=1).pack(fill=tk.X, padx=20, pady=(4, 8))

        def abrir_config_db():
            from configurador import mostrar_configurador
            mostrar_configurador(win, motivo='manual')

        ttk.Button(win, text="🔌 Reconfigurar conexión a MySQL",
                   command=abrir_config_db,
                   style='Neutral.TButton').pack(pady=(0, 16))

    def abrir_backup(self):
        from modulos.backup_module import BackupWindow
        BackupWindow(self.root, self.db, self.usuario)

    def abrir_busqueda_movimientos(self):
        from modulos.movimientos_busqueda import MovimientosWindow
        MovimientosWindow(self.root, self.db, self.C, self.usuario)

    def abrir_categorias(self):
        from modulos.categorias_module import CategoriasWindow
        CategoriasWindow(self.root, self.db, self.usuario)
        self._refrescar_cats()

    def abrir_importar_excel(self):
        from modulos.importar_excel import ImportarExcelWindow
        w = ImportarExcelWindow(self.root, self.db, self.C, self.usuario)
        w.win.bind('<Destroy>', lambda e: self.cargar_productos())

    def abrir_analizador_excel(self):
        from modulos.excel_analysis import ExcelAnalyzer
        ExcelAnalyzer(self.root).open_window()

    def abrir_gestion_usuarios(self):
        from modulos.users_module import UsersWindow
        UsersWindow(self.root, self.db, self.usuario, self.C)

    def abrir_gestion_roles(self):
        from modulos.users_module import RolesWindow
        RolesWindow(self.root, self.db, self.usuario, self.C)

    def abrir_proveedores(self):
        from modulos.suppliers_module import SuppliersWindow
        SuppliersWindow(self.root, self.db, self.usuario, self.C)
        self._refrescar_combo_proveedores()

    def abrir_log_actividad(self):
        from modulos.activity_log_module import LogWindow
        LogWindow(self.root, self.db)

    # ── Mi Cuenta ─────────────────────────────────────────────────────────────

    def cambiar_password(self):
        win = tk.Toplevel(self.root)
        win.title("🔑 Cambiar Contraseña")
        win.configure(bg=self.C['bg']); win.grab_set()
        configurar_ventana(
            win,
            width=430,
            height=300,
            min_width=430,
            min_height=300,
            resizable=(False, False),
        )
        frm = ttk.Frame(win)
        frm.pack(fill=tk.X, expand=True, padx=20, pady=20)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text="🔑 Cambiar Contraseña",
                  style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 14))
        entries = {}
        for i, (lbl, key) in enumerate([
            ("Contraseña actual:", 'actual'),
            ("Nueva contraseña:",  'nueva'),
            ("Confirmar nueva:",   'confirmar'),
        ], 1):
            ttk.Label(frm, text=lbl).grid(row=i, column=0, sticky='e', padx=8, pady=6)
            e = ttk.Entry(frm, width=20, show='*'); e.grid(row=i, column=1, pady=6, sticky='ew')
            entries[key] = e
        msg_lbl = tk.Label(win, text='', font=('Segoe UI', 9),
                           bg=self.C['bg'], fg=self.C['danger'])
        msg_lbl.pack()

        def guardar():
            actual = entries['actual'].get(); nueva = entries['nueva'].get()
            if nueva != entries['confirmar'].get():
                msg_lbl.config(text="Las contraseñas no coinciden."); return
            if len(nueva) < 4:
                msg_lbl.config(text="Mínimo 4 caracteres."); return
            ok, texto = self.db.cambiar_password(self.usuario['id'], actual, nueva)
            if ok:
                self.db.registrar_log(self.usuario['id'], self.usuario['username'],
                                      'Cambiar contraseña')
                win.destroy(); self._toast("✅ Contraseña actualizada", 'success')
            else:
                msg_lbl.config(text=texto)

        win.bind('<Return>', lambda e: guardar())
        ttk.Button(win, text="Guardar", command=guardar).pack(pady=10)

    # ── Sesión ────────────────────────────────────────────────────────────────

    def _cerrar_sesion(self):
        self._cancelar_auto_refresh()
        try:
            self.db.registrar_log(self.usuario['id'], self.usuario['username'], 'Cerrar sesión')
        except Exception:
            pass
        plt.close('all')
        for w in self.root.winfo_children(): w.destroy()
        self.root.withdraw()
        from main import mostrar_login
        usuario = mostrar_login(self.root, self.db)
        if not usuario:
            self.db.disconnect(); self.root.destroy(); return
        self.root.deiconify()
        InventoryManagementApp(self.root, self.db, usuario)

    def _resetear_inactividad(self, event=None):
        if self._inactividad_id:
            self.root.after_cancel(self._inactividad_id)
        self._inactividad_id = self.root.after(600000, self._cerrar_por_inactividad)

    def _cerrar_por_inactividad(self):
        messagebox.showwarning("⏱️ Sesión expirada",
                               "La sesión se cerró por 10 minutos de inactividad.")
        self._cerrar_sesion()

    def _confirmar_cierre(self):
        # La X no hace nada — el cierre es solo por el botón del sidebar
        pass

    def _abrir_manual(self):
        base = os.path.dirname(os.path.abspath(__file__))
        ruta = os.path.join(base, '..', 'manual_usuario.pdf')
        if not os.path.exists(ruta):
            messagebox.showwarning("⚠️", "No se encontró manual_usuario.pdf"); return
        try:
            if sys.platform == 'win32':    os.startfile(ruta)
            elif sys.platform == 'darwin': subprocess.Popen(['open', ruta])
            else:                          subprocess.Popen(['xdg-open', ruta])
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo abrir el manual:\n{e}")

    def _acerca_de(self):
        messagebox.showinfo("ℹ️ Acerca de",
                            f"Inventoryx\n{self._empresa_nombre}\n\n"
                            "Sistema de Gestión de Inventario\n"
                            "Versión 4.0  •  Python + Tkinter + MySQL\n\n© 2026 - Equipo STS")

    def cerrar(self):
        self._confirmar_cierre()


def _ordenar_tree(tree, col, reverse):
    data = [(tree.set(k, col), k) for k in tree.get_children('')]
    try:
        data.sort(key=lambda t: float(t[0].replace('$','').replace(',','')),
                  reverse=reverse)
    except ValueError:
        data.sort(reverse=reverse)
    for i, (_, k) in enumerate(data):
        tree.move(k, '', i)
    tree.heading(col, command=lambda: _ordenar_tree(tree, col, not reverse))
