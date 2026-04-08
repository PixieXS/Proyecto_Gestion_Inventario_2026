import json
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

from gui.reportes_dashboard_charts import ReportesDashboardChartsMixin
from gui.reportes_dashboard_dynamic import ReportesDashboardDynamicMixin
from gui.reportes_dashboard_config import (
    CATEGORY_METRICS,
    PRODUCT_METRICS,
    REPORTES_DISPONIBLES,
    RANK_CHART_TYPES,
    SUPPLIER_METRICS,
    TOP_OPTIONS,
    TREND_CHART_TYPES,
    TREND_METRICS,
    TREND_OPTIONS,
    as_float,
    as_int,
)
from gui.ui_helpers import ajustar_ventana_a_contenido, bloquear_columnas, configurar_ventana


class CentroReportesWindow(ReportesDashboardDynamicMixin, ReportesDashboardChartsMixin):
    def __init__(self, master, db, C, usuario, tipo_inicial="resumen_general", filtros_iniciales=None, tab_inicial="dashboard"):
        self.master = master
        self.db = db
        self.C = C
        self.usuario = usuario
        self.tipo_inicial = tipo_inicial or "resumen_general"
        self.filtros_iniciales = dict(filtros_iniciales or {})
        self.tab_inicial = tab_inicial or "dashboard"
        self._refresh_id = None
        self._canvas_charts = {}
        self._reportes_disponibles = self._filtrar_reportes_disponibles()
        if self.tipo_inicial not in {code for code, _label in self._reportes_disponibles}:
            self.tipo_inicial = self._reportes_disponibles[0][0]
        self._reportes_map = {label: code for code, label in self._reportes_disponibles}
        self._reportes_labels = {code: label for code, label in self._reportes_disponibles}

        self._cargar_catalogos()
        self._crear_ventana()
        self._crear_variables()
        self._crear_variables_dinamicas()
        self._construir_ui()
        self._aplicar_filtros_iniciales()
        self._consultar()
        self._seleccionar_tab_inicial()

    def _perm(self, permiso):
        return self.db.tiene_permiso(self.usuario, permiso)

    def _filtrar_reportes_disponibles(self):
        reportes = []
        for codigo, etiqueta in REPORTES_DISPONIBLES:
            if codigo == "comparativo_fechas":
                if not self._perm("reporte_fechas"):
                    continue
            elif not self._perm("ver_reportes"):
                continue
            reportes.append((codigo, etiqueta))
        return reportes or [REPORTES_DISPONIBLES[0]]

    def _permiso_exportacion_actual(self):
        tipo = getattr(self, "reporte_actual", {}).get(
            "tipo",
            self._reportes_map.get(self.var_tipo.get(), self.tipo_inicial),
        )
        if tipo in {"inventario_valorizado", "stock_critico", "sin_movimiento"}:
            return "exportar_inventario"
        if tipo in {"movimientos_usuario", "entradas_vs_salidas"}:
            return "exportar_movimientos"
        return "exportar_todo"

    def _puede_exportar_actual(self):
        permiso = self._permiso_exportacion_actual()
        if permiso == "exportar_todo":
            return self._perm("exportar_todo")
        return self._perm(permiso) or self._perm("exportar_todo")

    def _actualizar_estado_exportacion(self):
        estado = "normal" if self._puede_exportar_actual() else "disabled"
        for btn in (getattr(self, "btn_exportar_pdf", None), getattr(self, "btn_exportar_excel", None)):
            if btn is not None:
                btn.config(state=estado)

    def _cargar_catalogos(self):
        fuentes = self.db.obtener_fuentes_reportes()
        self.catalogos = fuentes

        self.map_proveedores = {"Todos": None}
        for proveedor in fuentes.get("proveedores", []):
            self.map_proveedores[proveedor.get("nombre") or f"Proveedor {proveedor.get('id')}"] = proveedor.get("id")

        self.map_productos = {"Todos": None}
        for producto in fuentes.get("productos", []):
            codigo = producto.get("codigo") or producto.get("id")
            nombre = producto.get("nombre") or f"Producto {producto.get('id')}"
            etiqueta = f"#{producto.get('id')} | {codigo} | {nombre}"
            self.map_productos[etiqueta] = producto.get("id")

        self.map_usuarios = {"Todos": None}
        for usuario in fuentes.get("usuarios", []):
            username = usuario.get("username") or f"usuario_{usuario.get('id')}"
            nombre = usuario.get("nombre_completo") or username
            self.map_usuarios[f"#{usuario.get('id')} | {username} | {nombre}"] = usuario.get("id")

        self.map_estados = {
            "Activos": "activos",
            "Inactivos": "inactivos",
            "Stock bajo": "stock_bajo",
            "Sin stock": "sin_stock",
            "Todos": "todos",
        }

    def _crear_ventana(self):
        self.win = tk.Toplevel(self.master)
        self.win.title("Centro de Reportes")
        self.win.configure(bg=self.C["bg"])
        configurar_ventana(self.win, size="main", min_width=1220, min_height=820)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._cerrar)

    def _crear_variables(self):
        hoy = datetime.now().date()
        self._fecha_inicio_default = (hoy - timedelta(days=30)).isoformat()
        self._fecha_fin_default = hoy.isoformat()
        self.filtros_colapsados = False
        self.var_tipo = tk.StringVar(value=self._reportes_labels.get(self.tipo_inicial, self._reportes_disponibles[0][1]))
        self.var_fecha_inicio = tk.StringVar(value=self._fecha_inicio_default)
        self.var_fecha_fin = tk.StringVar(value=self._fecha_fin_default)
        self.var_categoria = tk.StringVar(value="Todas")
        self.var_proveedor = tk.StringVar(value="Todos")
        self.var_producto = tk.StringVar(value="Todos")
        self.var_tipo_mov = tk.StringVar(value="Todos")
        self.var_usuario = tk.StringVar(value="Todos")
        self.var_estado = tk.StringVar(value="Activos")

        self.chart_state = {
            "categorias": {"metric": tk.StringVar(value="Valor inventario"), "type": tk.StringVar(value="Barras horizontales"), "limit": tk.StringVar(value="Top 10")},
            "productos": {"metric": tk.StringVar(value="Movimientos"), "type": tk.StringVar(value="Barras horizontales"), "limit": tk.StringVar(value="Top 10")},
            "proveedores": {"metric": tk.StringVar(value="Valor inventario"), "type": tk.StringVar(value="Barras verticales"), "limit": tk.StringVar(value="Top 10")},
            "tendencia": {"metric": tk.StringVar(value="Entradas"), "type": tk.StringVar(value="Linea"), "limit": tk.StringVar(value="Ultimos 15")},
        }
        self.chart_blueprints = {
            "categorias": {"title": "Distribucion por categoria", "subtitle": "Compara peso de stock, valor o cantidad de productos.", "dataset": "categorias", "label_key": "categoria", "metric_options": CATEGORY_METRICS, "type_options": RANK_CHART_TYPES, "limit_options": TOP_OPTIONS},
            "productos": {"title": "Top productos", "subtitle": "Prioriza productos visibles por actividad, stock o valor.", "dataset": "productos", "label_key": "producto", "metric_options": PRODUCT_METRICS, "type_options": RANK_CHART_TYPES, "limit_options": TOP_OPTIONS},
            "proveedores": {"title": "Analisis por proveedor", "subtitle": "Resume concentracion del inventario filtrado por proveedor.", "dataset": "proveedores", "label_key": "proveedor", "metric_options": SUPPLIER_METRICS, "type_options": RANK_CHART_TYPES, "limit_options": TOP_OPTIONS},
            "tendencia": {"title": "Tendencia temporal", "subtitle": "Evolucion del flujo de inventario segun el rango aplicado.", "dataset": "movimientos_fecha", "label_key": "fecha", "metric_options": TREND_METRICS, "type_options": TREND_CHART_TYPES, "limit_options": TREND_OPTIONS},
        }

    def _construir_ui(self):
        surface = self.C.get("surface", self.C["bg"])

        hdr = tk.Frame(self.win, bg=self.C["header_bg"], height=56)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        left = tk.Frame(hdr, bg=self.C["header_bg"])
        left.pack(side=tk.LEFT, fill=tk.Y, padx=14, pady=8)
        tk.Label(left, text="Centro BI", font=("Segoe UI", 8, "bold"), bg=self.C["header_bg"], fg=self.C.get("muted", "#CBD5E1")).pack(anchor="w")
        tk.Label(left, text="Reportes y analitica", font=("Segoe UI", 13, "bold"), bg=self.C["header_bg"], fg="white").pack(anchor="w")

        right = tk.Frame(hdr, bg=self.C["header_bg"])
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=14, pady=8)
        tk.Label(right, text=self.usuario.get("nombre_completo") or self.usuario.get("username"), font=("Segoe UI", 9, "bold"), bg=self.C["header_bg"], fg="white", justify="right").pack(anchor="e")
        tk.Label(right, text=datetime.now().strftime("%d/%m/%Y %H:%M"), font=("Segoe UI", 8), bg=self.C["header_bg"], fg=self.C.get("muted", "#CBD5E1"), justify="right").pack(anchor="e", pady=(1, 0))

        self.body = tk.Frame(self.win, bg=self.C["bg"])
        self.body.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.body.columnconfigure(0, weight=1)
        self.body.rowconfigure(1, weight=1)

        self.filtros_card = tk.Frame(self.body, bg=surface, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        self.filtros_card.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.filtros_card.columnconfigure(0, weight=1)

        filtros_head = tk.Frame(self.filtros_card, bg=surface)
        filtros_head.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 5))
        filtros_head.columnconfigure(0, weight=1)

        info = tk.Frame(filtros_head, bg=surface)
        info.grid(row=0, column=0, sticky="w")
        tk.Label(info, text="Contexto del reporte", font=("Segoe UI", 9, "bold"), bg=surface, fg=self.C["text"]).pack(anchor="w")

        botones = tk.Frame(filtros_head, bg=surface)
        botones.grid(row=0, column=1, sticky="e")
        ttk.Button(botones, text="Consultar", command=lambda: self._consultar(registrar_historial=True)).pack(side=tk.LEFT, padx=3)
        ttk.Button(botones, text="Limpiar filtros", command=self._limpiar_filtros).pack(side=tk.LEFT, padx=3)
        self.btn_exportar_pdf = ttk.Button(botones, text="Exportar PDF", command=self._exportar_pdf)
        self.btn_exportar_pdf.pack(side=tk.LEFT, padx=3)
        self.btn_exportar_excel = ttk.Button(botones, text="Exportar Excel", command=self._exportar_excel)
        self.btn_exportar_excel.pack(side=tk.LEFT, padx=3)
        self.btn_toggle_filtros = ttk.Button(botones, text="Mostrar filtros", command=self._toggle_panel_filtros)
        self.btn_toggle_filtros.pack(side=tk.LEFT, padx=(6, 0))

        resumen = tk.Frame(self.filtros_card, bg="#F8FAFC", highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        resumen.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        resumen.columnconfigure(0, weight=1)
        self.lbl_filtros_resumen = tk.Label(resumen, text="", font=("Segoe UI", 8, "bold"), bg="#F8FAFC", fg=self.C["text"], anchor="w")
        self.lbl_filtros_resumen.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        self.lbl_filtros_detalle = tk.Label(resumen, text="", font=("Segoe UI", 8), bg="#F8FAFC", fg=self.C.get("muted", "#64748B"), anchor="w", justify="left", wraplength=1120)
        self.lbl_filtros_detalle.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))

        self.filtros_expandible = tk.Frame(self.filtros_card, bg=surface)
        self.filtros_expandible.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))
        self.filtros_expandible.columnconfigure(0, weight=1)

        tipo_frame = tk.Frame(self.filtros_expandible, bg=surface)
        tipo_frame.pack(fill=tk.X, pady=(0, 6))
        tk.Label(tipo_frame, text="Tipo de reporte", font=("Segoe UI", 8, "bold"), bg=surface, fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 4))
        self.cb_tipo = ttk.Combobox(tipo_frame, state="readonly", values=[label for _, label in self._reportes_disponibles], textvariable=self.var_tipo)
        self.cb_tipo.pack(fill=tk.X)

        grid = tk.Frame(self.filtros_expandible, bg=surface)
        grid.pack(fill=tk.X)
        for col in range(4):
            grid.columnconfigure(col, weight=1)

        self.e_fecha_inicio = self._campo_filtro(grid, "Fecha inicio", self.var_fecha_inicio, 0, 0)
        self.e_fecha_fin = self._campo_filtro(grid, "Fecha fin", self.var_fecha_fin, 0, 1)
        self.cb_categoria = self._combo_filtro(grid, "Categoria", ["Todas"] + self.catalogos.get("categorias", []), self.var_categoria, 0, 2)
        self.cb_proveedor = self._combo_filtro(grid, "Proveedor", list(self.map_proveedores.keys()), self.var_proveedor, 0, 3)
        self.cb_producto = self._combo_filtro(grid, "Producto", list(self.map_productos.keys()), self.var_producto, 1, 0)
        self.cb_tipo_mov = self._combo_filtro(grid, "Tipo movimiento", ["Todos", "Entrada", "Salida", "Ajuste"], self.var_tipo_mov, 1, 1)
        self.cb_usuario = self._combo_filtro(grid, "Usuario", list(self.map_usuarios.keys()), self.var_usuario, 1, 2)
        self.cb_estado = self._combo_filtro(grid, "Estado producto", list(self.map_estados.keys()), self.var_estado, 1, 3)

        self.nb = ttk.Notebook(self.body)
        self.nb.grid(row=1, column=0, sticky="nsew")
        self.tab_dashboard = tk.Frame(self.nb, bg=self.C["bg"])
        self.tab_historial = tk.Frame(self.nb, bg=self.C["bg"])
        self.nb.add(self.tab_dashboard, text="Dashboard")
        self._construir_tabs_dinamicos(surface)
        self.nb.add(self.tab_historial, text="Historial")
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed_centro_reportes)

        self._construir_tab_dashboard(surface)
        self._construir_tab_historial(surface)
        self._vincular_filtros()
        self._actualizar_estado_exportacion()
        self._aplicar_estado_panel_filtros()
        self._actualizar_panel_superior_por_tab()
        self.win.after(80, lambda: ajustar_ventana_a_contenido(self.win, extra_width=24, extra_height=24))

    def _campo_filtro(self, parent, label, variable, row, col):
        box = tk.Frame(parent, bg=parent["bg"])
        box.grid(row=row, column=col, sticky="ew", padx=4, pady=4)
        tk.Label(box, text=label, font=("Segoe UI", 8, "bold"), bg=parent["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 3))
        entry = ttk.Entry(box, textvariable=variable)
        entry.pack(fill=tk.X)
        return entry

    def _combo_filtro(self, parent, label, values, variable, row, col):
        box = tk.Frame(parent, bg=parent["bg"])
        box.grid(row=row, column=col, sticky="ew", padx=4, pady=4)
        tk.Label(box, text=label, font=("Segoe UI", 8, "bold"), bg=parent["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 3))
        combo = ttk.Combobox(box, state="readonly", values=values, textvariable=variable)
        combo.pack(fill=tk.X)
        return combo

    def _construir_tab_dashboard(self, card_bg):
        outer = tk.Frame(self.tab_dashboard, bg=self.C["bg"])
        outer.pack(fill=tk.BOTH, expand=True)

        sb_y = ttk.Scrollbar(outer, orient="vertical")
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.dashboard_canvas = tk.Canvas(outer, bg=self.C["bg"], highlightthickness=0, yscrollcommand=sb_y.set)
        self.dashboard_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_y.config(command=self.dashboard_canvas.yview)

        self.dashboard_content = tk.Frame(self.dashboard_canvas, bg=self.C["bg"])
        self.dashboard_window = self.dashboard_canvas.create_window((0, 0), window=self.dashboard_content, anchor="nw")
        self.dashboard_content.bind("<Configure>", lambda _e: self.dashboard_canvas.configure(scrollregion=self.dashboard_canvas.bbox("all")))
        self.dashboard_canvas.bind("<Configure>", lambda e: self.dashboard_canvas.itemconfigure(self.dashboard_window, width=e.width))

        self._section_header(self.dashboard_content, "Vista analitica", "Mismo contexto filtrado para tarjetas KPI, visualizaciones y detalle del reporte.").pack(fill=tk.X, padx=6, pady=(6, 10))

        contexto_card = tk.Frame(self.dashboard_content, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        contexto_card.pack(fill=tk.X, padx=6, pady=(0, 12))
        tk.Label(contexto_card, text="Contexto aplicado", font=("Segoe UI", 11, "bold"), bg=card_bg, fg=self.C["text"]).pack(anchor="w", padx=16, pady=(14, 4))
        self.lbl_contexto = tk.Label(contexto_card, text="Sin filtros adicionales.", font=("Segoe UI", 9), bg=card_bg, fg=self.C.get("muted", "#64748B"), justify="left", wraplength=1200)
        self.lbl_contexto.pack(anchor="w", padx=16)
        self.frm_contexto_chips = tk.Frame(contexto_card, bg=card_bg)
        self.frm_contexto_chips.pack(fill=tk.X, padx=10, pady=(8, 14))

        self.frm_kpis = tk.Frame(self.dashboard_content, bg=self.C["bg"])
        self.frm_kpis.pack(fill=tk.X, padx=2, pady=(0, 10))

        if self._perm("ver_graficos"):
            self._section_header(self.dashboard_content, "Visualizaciones", "Cada panel permite cambiar metrica, tipo de grafico y cantidad de registros visibles.").pack(fill=tk.X, padx=6, pady=(0, 10))
            self.frm_charts = tk.Frame(self.dashboard_content, bg=self.C["bg"])
            self.frm_charts.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 12))
            self.frm_charts.columnconfigure(0, weight=1)
            self.frm_charts.columnconfigure(1, weight=1)
            self.frm_charts.rowconfigure(0, weight=1)
            self.frm_charts.rowconfigure(1, weight=1)
            self.chart_panels = {}
            posiciones = {"categorias": (0, 0), "productos": (0, 1), "proveedores": (1, 0), "tendencia": (1, 1)}
            for key, blueprint in self.chart_blueprints.items():
                row, col = posiciones[key]
                self.chart_panels[key] = self._crear_panel_chart(self.frm_charts, key, blueprint, row, col, card_bg)
        else:
            self.frm_charts = None
            aviso = tk.Frame(self.dashboard_content, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
            aviso.pack(fill=tk.X, padx=6, pady=(0, 12))
            tk.Label(aviso, text="No tienes permiso para ver graficos en este modulo.", font=("Segoe UI", 10, "bold"), bg=card_bg, fg=self.C["text"]).pack(anchor="w", padx=16, pady=(16, 2))
            tk.Label(aviso, text="La tabla del reporte y las exportaciones siguen disponibles con los filtros actuales.", font=("Segoe UI", 9), bg=card_bg, fg=self.C.get("muted", "#64748B")).pack(anchor="w", padx=16, pady=(0, 16))

        self._section_header(self.dashboard_content, "Detalle del reporte", "Vista tabular para revisar registros, resumen ejecutivo y datos listos para exportar.").pack(fill=tk.X, padx=6, pady=(0, 10))
        preview_card = tk.Frame(self.dashboard_content, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        preview_card.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        head = tk.Frame(preview_card, bg=card_bg)
        head.pack(fill=tk.X, padx=16, pady=(14, 10))
        self.lbl_reporte = tk.Label(head, text="Reporte", font=("Segoe UI", 13, "bold"), bg=card_bg, fg=self.C["text"])
        self.lbl_reporte.pack(anchor="w")
        self.lbl_resumen = tk.Label(head, text="", font=("Segoe UI", 9), bg=card_bg, fg=self.C.get("muted", "#64748B"), justify="left", wraplength=1200)
        self.lbl_resumen.pack(anchor="w", pady=(4, 0))

        self.frm_resumen_tarjetas = tk.Frame(preview_card, bg=card_bg)
        self.frm_resumen_tarjetas.pack(fill=tk.X, padx=10, pady=(0, 10))

        table_frame = tk.Frame(preview_card, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        self.tree_preview = ttk.Treeview(table_frame, show="headings")
        sb_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree_preview.yview)
        sb_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree_preview.xview)
        self.tree_preview.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        self.tree_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x.pack(side=tk.BOTTOM, fill=tk.X)
        bloquear_columnas(self.tree_preview)
        self.tree_preview.tag_configure("row_even", background="#FFFFFF")
        self.tree_preview.tag_configure("row_odd", background="#F8FAFC")
        self.tree_preview.tag_configure("critico", foreground=self.C.get("danger", "#991B1B"))
        self.tree_preview.tag_configure("positivo", foreground=self.C.get("secondary", "#166534"))
        self.tree_preview.tag_configure("negativo", foreground=self.C.get("danger", "#991B1B"))

        footer = tk.Frame(preview_card, bg=card_bg)
        footer.pack(fill=tk.X, padx=16, pady=(0, 14))
        self.lbl_registros = tk.Label(footer, text="0 registros", font=("Segoe UI", 9, "bold"), bg=card_bg, fg=self.C["text"])
        self.lbl_registros.pack(side=tk.LEFT)
        self.lbl_actualizacion = tk.Label(footer, text="", font=("Segoe UI", 9), bg=card_bg, fg=self.C.get("muted", "#64748B"))
        self.lbl_actualizacion.pack(side=tk.RIGHT)

    def _crear_panel_chart(self, parent, key, blueprint, row, col, card_bg):
        panel = tk.Frame(parent, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        panel.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        parent.grid_rowconfigure(row, weight=1)
        parent.grid_columnconfigure(col, weight=1)

        head = tk.Frame(panel, bg=card_bg)
        head.pack(fill=tk.X, padx=16, pady=(14, 8))
        tk.Label(head, text=blueprint["title"], font=("Segoe UI", 11, "bold"), bg=card_bg, fg=self.C["text"]).pack(anchor="w")
        tk.Label(head, text=blueprint["subtitle"], font=("Segoe UI", 9), bg=card_bg, fg=self.C.get("muted", "#64748B"), wraplength=520, justify="left").pack(anchor="w", pady=(3, 0))

        controls = tk.Frame(panel, bg=card_bg)
        controls.pack(fill=tk.X, padx=12, pady=(0, 8))
        combos = [
            self._chart_control(controls, "Metrica", list(blueprint["metric_options"].keys()), self.chart_state[key]["metric"], 0),
            self._chart_control(controls, "Grafico", list(blueprint["type_options"]), self.chart_state[key]["type"], 1),
            self._chart_control(controls, "Rango", list(blueprint["limit_options"]), self.chart_state[key]["limit"], 2),
        ]
        for combo in combos:
            combo.bind("<<ComboboxSelected>>", lambda _e: self._redibujar_dashboard())

        hint = tk.Label(panel, text="", font=("Segoe UI", 8), bg=card_bg, fg=self.C.get("muted", "#64748B"), anchor="w", justify="left")
        hint.pack(fill=tk.X, padx=16, pady=(0, 4))
        plot = tk.Frame(panel, bg=card_bg)
        plot.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        return {"panel": panel, "plot": plot, "hint": hint}

    def _chart_control(self, parent, label, values, variable, column):
        parent.columnconfigure(column, weight=1)
        box = tk.Frame(parent, bg=parent["bg"])
        box.grid(row=0, column=column, sticky="ew", padx=4, pady=2)
        tk.Label(box, text=label, font=("Segoe UI", 8, "bold"), bg=parent["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 4))
        combo = ttk.Combobox(box, state="readonly", values=values, textvariable=variable)
        combo.pack(fill=tk.X)
        return combo

    def _construir_tab_historial(self, card_bg):
        card = tk.Frame(self.tab_historial, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        head = tk.Frame(card, bg=card_bg)
        head.pack(fill=tk.X, padx=16, pady=(14, 10))
        tk.Label(head, text="Historial de ejecuciones", font=("Segoe UI", 12, "bold"), bg=card_bg, fg=self.C["text"]).pack(anchor="w")
        tk.Label(head, text="Registro de vistas previas y exportaciones generadas desde el centro de reportes.", font=("Segoe UI", 9), bg=card_bg, fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(3, 0))

        table_frame = tk.Frame(card, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
        cols = ("Fecha", "Reporte", "Formato", "Usuario", "Registros", "Filtros")
        self.tree_historial = ttk.Treeview(table_frame, columns=cols, show="headings")
        sb_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree_historial.yview)
        self.tree_historial.configure(yscrollcommand=sb_y.set)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_historial.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for col, width in zip(cols, (140, 250, 110, 150, 90, 520)):
            self.tree_historial.heading(col, text=col)
            self.tree_historial.column(col, width=width, anchor="w")
        bloquear_columnas(self.tree_historial)

    def _section_header(self, parent, titulo, subtitulo):
        frame = tk.Frame(parent, bg=self.C["bg"])
        tk.Label(frame, text=titulo, font=("Segoe UI", 13, "bold"), bg=self.C["bg"], fg=self.C["text"]).pack(anchor="w")
        tk.Label(frame, text=subtitulo, font=("Segoe UI", 9), bg=self.C["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(2, 0))
        return frame

    def _detalle_filtros_activos_ui(self):
        detalles = []
        if self.var_categoria.get() != "Todas":
            detalles.append(f"Categoria: {self.var_categoria.get()}")
        if self.var_proveedor.get() != "Todos":
            detalles.append(f"Proveedor: {self.var_proveedor.get()}")
        if self.var_producto.get() != "Todos":
            detalles.append(f"Producto: {self.var_producto.get()}")
        if self.var_tipo_mov.get() != "Todos":
            detalles.append(f"Movimiento: {self.var_tipo_mov.get()}")
        if self.var_usuario.get() != "Todos":
            detalles.append(f"Usuario: {self.var_usuario.get()}")
        if self.var_estado.get() != "Activos":
            detalles.append(f"Estado: {self.var_estado.get()}")
        if self.var_fecha_inicio.get().strip() != self._fecha_inicio_default or self.var_fecha_fin.get().strip() != self._fecha_fin_default:
            detalles.append("Periodo ajustado")
        return detalles

    def _actualizar_resumen_panel_filtros(self):
        if not hasattr(self, "lbl_filtros_resumen"):
            return
        activos = self._detalle_filtros_activos_ui()
        periodo = f"{self.var_fecha_inicio.get().strip() or 'Inicio'} a {self.var_fecha_fin.get().strip() or 'Hoy'}"
        reporte = self.var_tipo.get().strip() or "Reporte"
        self.lbl_filtros_resumen.config(
            text=f"Reporte: {reporte}   |   Periodo: {periodo}   |   Filtros activos: {len(activos)}"
        )
        if activos:
            detalle = "Activos: " + " | ".join(activos)
        elif self.filtros_colapsados:
            detalle = ""
        else:
            detalle = "Ajusta aqui el contexto y vuelve a ocultar el panel para priorizar el area analitica."
        self.lbl_filtros_detalle.config(text=detalle)
        if detalle:
            self.lbl_filtros_detalle.grid()
        else:
            self.lbl_filtros_detalle.grid_remove()
        if hasattr(self, "btn_toggle_filtros"):
            self.btn_toggle_filtros.config(text="Mostrar filtros" if self.filtros_colapsados else "Ocultar filtros")

    def _clave_tab_activa(self):
        if not hasattr(self, "nb"):
            return "dashboard"
        try:
            actual = self.nb.nametowidget(self.nb.select())
        except Exception:
            actual = getattr(self, "tab_dashboard", None)
        mapping = {
            getattr(self, "tab_dashboard", None): "dashboard",
            getattr(self, "tab_dynamic_charts", None): "graficos_dinamicos",
            getattr(self, "tab_custom_reports", None): "reportes_personalizados",
            getattr(self, "tab_historial", None): "historial",
        }
        return mapping.get(actual, "dashboard")

    def _actualizar_panel_superior_por_tab(self, _event=None):
        tab_key = self._clave_tab_activa()
        if tab_key == "dashboard":
            self.filtros_card.grid()
            self._aplicar_estado_panel_filtros()
        else:
            self.filtros_card.grid_remove()
        self.body.update_idletasks()

    def _on_tab_changed_centro_reportes(self, _event=None):
        self._actualizar_panel_superior_por_tab()

    def _aplicar_estado_panel_filtros(self):
        if not hasattr(self, "filtros_expandible"):
            return
        if self.filtros_colapsados:
            self.filtros_expandible.grid_remove()
        else:
            self.filtros_expandible.grid()
        self._actualizar_resumen_panel_filtros()
        self.body.update_idletasks()

    def _toggle_panel_filtros(self):
        self.filtros_colapsados = not self.filtros_colapsados
        self._aplicar_estado_panel_filtros()

    def _vincular_filtros(self):
        for combo in (self.cb_tipo, self.cb_categoria, self.cb_proveedor, self.cb_producto, self.cb_tipo_mov, self.cb_usuario, self.cb_estado):
            combo.bind("<<ComboboxSelected>>", lambda _e: self._programar_consulta())
        for entry in (self.e_fecha_inicio, self.e_fecha_fin):
            entry.bind("<KeyRelease>", lambda _e: self._programar_consulta())
            entry.bind("<FocusOut>", lambda _e: self._programar_consulta())
            entry.bind("<Return>", lambda _e: self._programar_consulta())

    def _aplicar_filtros_iniciales(self):
        if self.filtros_iniciales.get("fecha_inicio"):
            self.var_fecha_inicio.set(self.filtros_iniciales["fecha_inicio"])
        if self.filtros_iniciales.get("fecha_fin"):
            self.var_fecha_fin.set(self.filtros_iniciales["fecha_fin"])
        if self.filtros_iniciales.get("categoria"):
            self.var_categoria.set(self.filtros_iniciales["categoria"])
        if self.filtros_iniciales.get("tipo_movimiento"):
            self.var_tipo_mov.set(self.filtros_iniciales["tipo_movimiento"].title())
        if self.filtros_iniciales.get("estado_producto"):
            for label, code in self.map_estados.items():
                if code == self.filtros_iniciales["estado_producto"]:
                    self.var_estado.set(label)
                    break
        if self.filtros_iniciales.get("id_proveedor"):
            for label, value in self.map_proveedores.items():
                if value == self.filtros_iniciales["id_proveedor"]:
                    self.var_proveedor.set(label)
                    break
        if self.filtros_iniciales.get("id_producto"):
            for label, value in self.map_productos.items():
                if value == self.filtros_iniciales["id_producto"]:
                    self.var_producto.set(label)
                    break
        if self.filtros_iniciales.get("id_usuario"):
            for label, value in self.map_usuarios.items():
                if value == self.filtros_iniciales["id_usuario"]:
                    self.var_usuario.set(label)
                    break
        self._actualizar_resumen_panel_filtros()

    def _programar_consulta(self):
        if self._refresh_id:
            try:
                self.win.after_cancel(self._refresh_id)
            except Exception:
                pass
        self._actualizar_estado_exportacion()
        self._actualizar_resumen_panel_filtros()
        self._refresh_id = self.win.after(450, self._consultar)

    def _obtener_filtros(self):
        return {
            "fecha_inicio": self.var_fecha_inicio.get().strip(),
            "fecha_fin": self.var_fecha_fin.get().strip(),
            "categoria": "" if self.var_categoria.get() == "Todas" else self.var_categoria.get().strip(),
            "id_proveedor": self.map_proveedores.get(self.var_proveedor.get()),
            "id_producto": self.map_productos.get(self.var_producto.get()),
            "tipo_movimiento": "" if self.var_tipo_mov.get() == "Todos" else self.var_tipo_mov.get().strip(),
            "id_usuario": self.map_usuarios.get(self.var_usuario.get()),
            "estado_producto": self.map_estados.get(self.var_estado.get(), "activos"),
        }

    def _consultar(self, registrar_historial=False):
        self._refresh_id = None
        tipo = self._reportes_map.get(self.var_tipo.get(), "resumen_general")
        filtros = self._obtener_filtros()
        try:
            panel = self.db.obtener_panel_reportes(tipo, filtros)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo consultar el reporte:\n{exc}", parent=self.win)
            return

        self.panel_actual = panel
        self.reporte_actual = panel["reporte"]
        self.dashboard_actual = panel["dashboard"]
        self._actualizar_contexto(self.dashboard_actual.get("contexto", []))
        self._actualizar_kpis(self.dashboard_actual.get("kpis", {}))
        self._actualizar_dashboard(self.dashboard_actual)
        self._actualizar_preview(self.reporte_actual)
        self._cargar_historial(panel.get("historial", []))
        self._actualizar_estado_exportacion()
        self._actualizar_resumen_panel_filtros()
        if hasattr(self, "lbl_chart_status"):
            self.lbl_chart_status.config(
                text="Los filtros globales cambiaron. Usa 'Generar grafico' para refrescar la vista dinamica.",
                fg=self.C.get("muted", "#64748B"),
            )
        if hasattr(self, "lbl_report_status"):
            self.lbl_report_status.config(
                text="Los filtros globales cambiaron. Usa 'Previsualizar' para reconstruir el reporte personalizado.",
                fg=self.C.get("muted", "#64748B"),
            )
            self._actualizar_estado_exportacion_personalizada()

        if registrar_historial:
            self._registrar_historial("Vista previa")

    def _actualizar_contexto(self, contexto):
        contexto = list(contexto or [])
        resumen = " | ".join(f"{item.get('label')}: {item.get('value')}" for item in contexto) or "Sin filtros adicionales."
        self.lbl_contexto.config(text=resumen)
        for child in self.frm_contexto_chips.winfo_children():
            child.destroy()

        chips = contexto or [{"label": "Vista", "value": "Sin filtros adicionales"}]
        for idx, item in enumerate(chips):
            self.frm_contexto_chips.columnconfigure(idx % 4, weight=1)
            chip = tk.Frame(self.frm_contexto_chips, bg="#F8FAFC", highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
            chip.grid(row=idx // 4, column=idx % 4, sticky="ew", padx=6, pady=6)
            tk.Label(chip, text=item.get("label") or "Filtro", font=("Segoe UI", 8, "bold"), bg="#F8FAFC", fg=self.C.get("muted", "#64748B")).pack(anchor="w", padx=10, pady=(8, 0))
            tk.Label(chip, text=item.get("value") or "-", font=("Segoe UI", 9, "bold"), bg="#F8FAFC", fg=self.C["text"], wraplength=240, justify="left").pack(anchor="w", padx=10, pady=(2, 8))

    def _actualizar_kpis(self, kpis):
        for child in self.frm_kpis.winfo_children():
            child.destroy()

        definiciones = [
            ("Productos", kpis.get("total_productos", 0), self.C.get("primary", "#2563EB"), "Items visibles con los filtros activos."),
            ("Categorias", kpis.get("total_categorias", 0), "#0F766E", "Categorias representadas en el analisis."),
            ("Proveedores", kpis.get("total_proveedores", 0), "#D97706", "Proveedores presentes en el resultado."),
            ("Stock bajo", kpis.get("productos_stock_bajo", 0), self.C.get("danger", "#DC2626"), "Alertas que requieren seguimiento."),
            ("Valor inventario", kpis.get("valor_total_inventario", 0.0), self.C.get("primary", "#2563EB"), "Valorizacion al precio de venta actual."),
            ("Entradas", kpis.get("entradas_periodo", 0), "#0F766E", "Unidades recibidas durante el periodo."),
            ("Salidas", kpis.get("salidas_periodo", 0), self.C.get("danger", "#DC2626"), "Unidades despachadas durante el periodo."),
        ]

        for col in range(4):
            self.frm_kpis.columnconfigure(col, weight=1)

        for idx, (titulo, valor, color, nota) in enumerate(definiciones):
            row, col = divmod(idx, 4)
            card = tk.Frame(self.frm_kpis, bg="#FFFFFF", highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
            card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            tk.Frame(card, bg=color, height=4).pack(fill=tk.X)
            body = tk.Frame(card, bg="#FFFFFF")
            body.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)
            tk.Label(body, text=titulo.upper(), font=("Segoe UI", 8, "bold"), bg="#FFFFFF", fg=self.C.get("muted", "#64748B")).pack(anchor="w")
            fmt = "currency" if isinstance(valor, float) else "number"
            tk.Label(body, text=self._mostrar_valor(valor, fmt), font=("Segoe UI", 20, "bold"), bg="#FFFFFF", fg=color).pack(anchor="w", pady=(6, 4))
            tk.Label(body, text=nota, font=("Segoe UI", 8), bg="#FFFFFF", fg=self.C.get("muted", "#64748B"), wraplength=220, justify="left").pack(anchor="w")

    def _formato_columna(self, columna, fila):
        formatos = dict(self.reporte_actual.get("formatos") or {})
        fmt = formatos.get(columna)
        if fmt == "auto" and self.reporte_actual.get("tipo") == "comparativo_fechas":
            metrica = str(fila.get("Metrica") or "").lower()
            return "currency" if "valor" in metrica else "number"
        if fmt == "metric":
            valor = fila.get(columna)
            return "currency" if isinstance(valor, float) else "number"
        return fmt

    def _mostrar_valor(self, valor, fmt=None):
        if valor in (None, ""):
            return ""
        if fmt == "currency":
            return f"${as_float(valor):,.2f}"
        if fmt == "percent":
            return f"{as_float(valor):,.1f}%"
        if fmt == "number":
            return f"{as_int(valor):,}"
        if fmt == "date" and hasattr(valor, "strftime"):
            return valor.strftime("%d/%m/%Y")
        if fmt == "datetime" and hasattr(valor, "strftime"):
            return valor.strftime("%d/%m/%Y %H:%M")
        return str(valor)

    def _tags_fila(self, fila, index):
        tags = ["row_even" if index % 2 == 0 else "row_odd"]
        if fila.get("Stock") is not None and fila.get("Stock Minimo") is not None:
            if as_float(fila.get("Stock")) <= as_float(fila.get("Stock Minimo")):
                tags.append("critico")
        if fila.get("Balance") is not None:
            tags.append("positivo" if as_float(fila.get("Balance")) >= 0 else "negativo")
        return tuple(tags)

    def _ancho_preview_columna(self, columna, fmt, filas):
        max_len = len(columna)
        for fila in list(filas)[:40]:
            valor = self._mostrar_valor(fila.get(columna), fmt)
            max_len = max(max_len, max((len(linea) for linea in str(valor).splitlines()), default=0))
        if fmt in {"currency", "number", "percent"}:
            return min(max(120, max_len * 8 + 22), 170)
        if fmt in {"date", "datetime"}:
            return min(max(120, max_len * 8 + 22), 180)
        return min(max(130, max_len * 8 + 26), 320)

    def _actualizar_resumen_tarjetas(self, resumen):
        for child in self.frm_resumen_tarjetas.winfo_children():
            child.destroy()
        resumen = list((resumen or {}).items())
        if not resumen:
            return
        columnas = min(4, max(1, len(resumen)))
        for col in range(columnas):
            self.frm_resumen_tarjetas.columnconfigure(col, weight=1)
        for idx, (clave, valor) in enumerate(resumen):
            card = tk.Frame(self.frm_resumen_tarjetas, bg="#F8FAFC", highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
            card.grid(row=idx // columnas, column=idx % columnas, sticky="ew", padx=6, pady=6)
            tk.Label(card, text=str(clave), font=("Segoe UI", 8, "bold"), bg="#F8FAFC", fg=self.C.get("muted", "#64748B"), wraplength=220, justify="left").pack(anchor="w", padx=10, pady=(8, 2))
            tk.Label(card, text=self._mostrar_valor(valor, "currency" if isinstance(valor, float) else None), font=("Segoe UI", 11, "bold"), bg="#F8FAFC", fg=self.C["text"], wraplength=220, justify="left").pack(anchor="w", padx=10, pady=(0, 10))

    def _actualizar_preview(self, reporte):
        columnas = list(reporte.get("columnas") or [])
        filas = list(reporte.get("filas") or [])
        self.tree_preview.delete(*self.tree_preview.get_children())
        self.tree_preview.configure(columns=columnas)
        for col in columnas:
            fmt = self._formato_columna(col, filas[0] if filas else {})
            anchor = "e" if fmt in {"currency", "number", "percent"} else "w"
            self.tree_preview.heading(col, text=col)
            self.tree_preview.column(col, width=self._ancho_preview_columna(col, fmt, filas), anchor=anchor)
        for idx, fila in enumerate(filas):
            valores = [self._mostrar_valor(fila.get(col), self._formato_columna(col, fila)) for col in columnas]
            self.tree_preview.insert("", tk.END, values=valores, tags=self._tags_fila(fila, idx))
        self.lbl_reporte.config(text=reporte.get("titulo") or "Reporte")
        self.lbl_resumen.config(text=reporte.get("subtitulo") or "")
        self._actualizar_resumen_tarjetas(reporte.get("resumen") or {})
        self.lbl_registros.config(text=f"{len(filas)} registros")
        self.lbl_actualizacion.config(text=f"Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    def _resumen_filtros_historial(self, item):
        try:
            filtros = json.loads(item.get("filtros_json") or "{}")
        except Exception:
            filtros = {}
        partes = []
        for clave, valor in filtros.items():
            if valor in (None, "", "todos"):
                continue
            partes.append(f"{clave}={valor}")
        return ", ".join(partes)[:180] or "Sin filtros"

    def _cargar_historial(self, historial):
        self.tree_historial.delete(*self.tree_historial.get_children())
        for item in historial:
            fecha = item.get("fecha_generacion")
            if hasattr(fecha, "strftime"):
                fecha = fecha.strftime("%d/%m/%Y %H:%M")
            self.tree_historial.insert(
                "",
                tk.END,
                values=(
                    fecha or "",
                    item.get("titulo_reporte") or item.get("tipo_reporte") or "",
                    item.get("formato") or "",
                    item.get("username") or "Sistema",
                    item.get("total_registros") or 0,
                    self._resumen_filtros_historial(item),
                ),
            )

    def _empresa_info(self):
        return {
            "nombre": self.db.get_empresa_nombre(),
            "direccion": self.db.get_config("empresa_direccion", ""),
            "telefono": self.db.get_config("empresa_telefono", ""),
            "logo": self.db.get_empresa_logo(),
        }

    def _registrar_historial(self, formato):
        reporte = self.reporte_actual or {}
        filtros = self.panel_actual.get("filtros", {}) if hasattr(self, "panel_actual") else self._obtener_filtros()
        self.db.registrar_reporte_generado(
            reporte.get("tipo") or "reporte",
            reporte.get("titulo") or "Reporte",
            id_usuario=self.usuario.get("id"),
            username=self.usuario.get("username"),
            filtros=filtros,
            formato=formato,
            total_registros=len(reporte.get("filas") or []),
        )
        if formato != "Vista previa":
            self.db.registrar_log(
                self.usuario.get("id"),
                self.usuario.get("username"),
                f"Reporte {formato}",
                f"{reporte.get('titulo') or 'Reporte'} | {json.dumps(filtros, ensure_ascii=False)}",
            )
        self._cargar_historial(self.db.obtener_historial_reportes())

    def _exportar_pdf(self):
        if not self._puede_exportar_actual():
            messagebox.showwarning("Permiso requerido", "No tienes permiso para exportar este tipo de reporte.", parent=self.win)
            return
        from reportes_gen.reports import ReportGenerator

        if not hasattr(self, "reporte_actual"):
            self._consultar()
        ok, msg = ReportGenerator().generar_reporte_ejecutivo(
            self.reporte_actual,
            filtros=self.panel_actual.get("filtros", {}),
            usuario=self.usuario,
            empresa_info=self._empresa_info(),
            color_hex=self.C.get("primary", "#1f4788"),
        )
        if ok:
            self._registrar_historial("PDF")
            messagebox.showinfo("Reporte PDF", msg, parent=self.win)
        else:
            messagebox.showerror("Error", msg, parent=self.win)

    def _exportar_excel(self):
        if not self._puede_exportar_actual():
            messagebox.showwarning("Permiso requerido", "No tienes permiso para exportar este tipo de reporte.", parent=self.win)
            return
        from reportes_gen.export_excel import ExcelExporter

        if not hasattr(self, "reporte_actual"):
            self._consultar()
        ok, msg = ExcelExporter(db=self.db).exportar_reporte_ejecutivo(
            self.reporte_actual,
            filtros=self.panel_actual.get("filtros", {}),
            usuario=self.usuario,
            empresa_info=self._empresa_info(),
        )
        if ok:
            self._registrar_historial("Excel")
            messagebox.showinfo("Reporte Excel", f"Guardado en:\n{msg}", parent=self.win)
        else:
            messagebox.showerror("Error", msg, parent=self.win)

    def _limpiar_filtros(self):
        self.var_fecha_inicio.set(self._fecha_inicio_default)
        self.var_fecha_fin.set(self._fecha_fin_default)
        self.var_categoria.set("Todas")
        self.var_proveedor.set("Todos")
        self.var_producto.set("Todos")
        self.var_tipo_mov.set("Todos")
        self.var_usuario.set("Todos")
        self.var_estado.set("Activos")
        self._actualizar_resumen_panel_filtros()
        self._consultar()

    def _seleccionar_tab_inicial(self):
        mapping = {
            "dashboard": getattr(self, "tab_dashboard", None),
            "graficos_dinamicos": getattr(self, "tab_dynamic_charts", None),
            "reportes_personalizados": getattr(self, "tab_custom_reports", None),
            "historial": getattr(self, "tab_historial", None),
        }
        target = mapping.get(self.tab_inicial)
        if target is not None:
            try:
                self.nb.select(target)
            except Exception:
                pass
        self._actualizar_panel_superior_por_tab()

    def _cerrar(self):
        self._limpiar_canvases()
        plt.close("all")
        self.win.destroy()


class ReportesUIMixin:
    def _permite(self, permiso):
        return self.db.tiene_permiso(self.usuario, permiso)

    def abrir_centro_reportes(self, tipo_inicial="resumen_general", filtros_iniciales=None, tab_inicial="dashboard"):
        if not (self._permite("ver_reportes") or self._permite("reporte_fechas")):
            messagebox.showwarning("Permiso requerido", "No tienes permiso para abrir el centro de reportes.", parent=self.root)
            return
        return CentroReportesWindow(
            self.root,
            self.db,
            self.C,
            self.usuario,
            tipo_inicial=tipo_inicial,
            filtros_iniciales=filtros_iniciales,
            tab_inicial=tab_inicial,
        )

    def gen_reporte_inventario(self):
        self.abrir_centro_reportes("inventario_valorizado")

    def gen_reporte_movimientos(self):
        self.abrir_centro_reportes("entradas_vs_salidas")

    def gen_reporte_estadisticas(self):
        self.abrir_centro_reportes("resumen_general")

    def reporte_rango_fechas(self):
        if not self._permite("reporte_fechas"):
            messagebox.showwarning("Permiso requerido", "No tienes permiso para consultar reportes por fechas.", parent=self.root)
            return
        self.abrir_centro_reportes("comparativo_fechas")

    def exportar_inventario(self):
        if not (self._permite("exportar_inventario") or self._permite("exportar_todo")):
            messagebox.showwarning("Permiso requerido", "No tienes permiso para exportar inventario.", parent=self.root)
            return
        panel = self.db.obtener_panel_reportes("inventario_valorizado", {"estado_producto": "activos"})
        from reportes_gen.export_excel import ExcelExporter

        ok, ruta = ExcelExporter(db=self.db).exportar_reporte_ejecutivo(
            panel["reporte"],
            filtros=panel["filtros"],
            usuario=self.usuario,
            empresa_info={
                "nombre": self.db.get_empresa_nombre(),
                "direccion": self.db.get_config("empresa_direccion", ""),
                "telefono": self.db.get_config("empresa_telefono", ""),
                "logo": self.db.get_empresa_logo(),
            },
        )
        if ok:
            self.db.registrar_reporte_generado(panel["reporte"]["tipo"], panel["reporte"]["titulo"], self.usuario["id"], self.usuario["username"], panel["filtros"], "Excel", len(panel["reporte"]["filas"]))
            self.db.registrar_log(self.usuario["id"], self.usuario["username"], "Reporte Excel", panel["reporte"]["titulo"])
            messagebox.showinfo("Inventario Excel", f"Guardado en:\n{ruta}", parent=self.root)
        else:
            messagebox.showerror("Error", ruta, parent=self.root)

    def exportar_movimientos(self):
        self.abrir_centro_reportes("movimientos_usuario")

    def exportar_todo(self):
        self.abrir_centro_reportes("resumen_general")

    def gen_reporte_categorias(self):
        self.abrir_centro_reportes("resumen_general")

    def gen_reporte_dados_baja(self):
        self.abrir_centro_reportes("inventario_valorizado", {"estado_producto": "inactivos"})

    def exportar_inventario_completo(self):
        self.exportar_inventario()

    def backup_bd(self):
        if not self._permite("backup_bd"):
            messagebox.showwarning("Permiso requerido", "No tienes permiso para crear respaldos de la base de datos.", parent=self.root)
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension=".sql",
            filetypes=[("SQL", "*.sql"), ("Todos", "*.*")],
            initialfile=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
        )
        if not ruta:
            return
        ok, resultado = self.db.backup_base_datos(ruta)
        if ok:
            self.db.registrar_log(self.usuario["id"], self.usuario["username"], "Backup BD", ruta)
            messagebox.showinfo("Backup", f"Backup guardado en:\n{resultado}", parent=self.root)
        else:
            messagebox.showerror("Error", resultado, parent=self.root)
