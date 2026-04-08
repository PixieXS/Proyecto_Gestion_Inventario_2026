import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gui.ui_helpers import bloquear_columnas


CHART_TYPE_OPTIONS = ("Barras verticales", "Barras horizontales", "Linea", "Area", "Pastel", "Dona")
CHART_LIMIT_OPTIONS = ("Top 5", "Top 10", "Top 15", "Top 20", "Todos", "Ultimos 15", "Ultimos 30")
AGGREGATION_OPTIONS = ("Suma", "Promedio", "Maximo", "Minimo")


class ReportesDashboardDynamicMixin:
    def _crear_variables_dinamicas(self):
        self.dynamic_catalog = self.db.obtener_catalogo_reportes_dinamicos()
        self.dynamic_sources = self.dynamic_catalog.get("sources", {})
        self.dynamic_source_keys = list(self.dynamic_sources.keys())
        self.dynamic_source_labels = {key: data["label"] for key, data in self.dynamic_sources.items()}
        self.dynamic_label_to_source = {label: key for key, label in self.dynamic_source_labels.items()}

        chart_key = self.dynamic_source_keys[0] if self.dynamic_source_keys else ""
        report_key = self.dynamic_source_keys[0] if self.dynamic_source_keys else ""
        chart_defaults = self.dynamic_sources.get(chart_key, {}).get("default_chart", {})

        self.var_chart_source = tk.StringVar(value=self.dynamic_source_labels.get(chart_key, ""))
        self.var_chart_x = tk.StringVar(value="")
        self.var_chart_y = tk.StringVar(value="")
        self.var_chart_agg = tk.StringVar(value=chart_defaults.get("aggregation", "Suma"))
        self.var_chart_type = tk.StringVar(value=chart_defaults.get("chart_type", "Barras verticales"))
        self.var_chart_limit = tk.StringVar(value=chart_defaults.get("limit", "Top 10"))

        self.var_report_source = tk.StringVar(value=self.dynamic_source_labels.get(report_key, ""))
        self.var_report_sort = tk.StringVar(value="")
        self.var_report_sort_dir = tk.StringVar(value="desc")
        self.var_report_subtotal = tk.StringVar(value="")
        self.var_report_summary = tk.BooleanVar(value=True)
        self.var_report_totals = tk.BooleanVar(value=True)
        self.var_report_subtotals = tk.BooleanVar(value=False)

        self.dynamic_filters = {"chart": [], "report": []}
        self.dynamic_filter_builders = {}
        self.reporte_personalizado_actual = None
        self.grafico_dinamico_actual = None
        self.chart_builder_collapsed = False
        self.report_builder_collapsed = False
        self.chart_builder_width = 350
        self.report_builder_width = 400
        self.chart_advanced_open = True
        self.report_columns_open = True
        self.report_advanced_open = True
        self._dynamic_chart_resize_after = None
        self._dynamic_chart_plot_size = (0, 0)
        self._chart_builder_synced = False
        self._report_builder_synced = False

    def _dynamic_source_key(self, scope):
        label = self.var_chart_source.get() if scope == "chart" else self.var_report_source.get()
        return self.dynamic_label_to_source.get(label, "")

    def _dynamic_source(self, scope):
        return self.dynamic_sources.get(self._dynamic_source_key(scope), {})

    def _dynamic_fields(self, scope):
        source = self._dynamic_source(scope)
        fields = list(source.get("fields") or [])
        return fields, {field["key"]: field for field in fields}, {field["label"]: field["key"] for field in fields}

    def _dynamic_permission_for_source(self, source_key):
        if source_key in {"productos", "categorias", "proveedores"}:
            return "exportar_inventario"
        if source_key in {"movimientos", "usuarios"}:
            return "exportar_movimientos"
        return "exportar_todo"

    def _can_export_dynamic_source(self, source_key):
        permiso = self._dynamic_permission_for_source(source_key)
        if permiso == "exportar_todo":
            return self._perm("exportar_todo")
        return self._perm(permiso) or self._perm("exportar_todo")

    def _construir_tabs_dinamicos(self, card_bg):
        self.tab_dynamic_charts = tk.Frame(self.nb, bg=self.C["bg"])
        self.tab_custom_reports = tk.Frame(self.nb, bg=self.C["bg"])
        self.nb.add(self.tab_dynamic_charts, text="Graficos dinamicos")
        self.nb.add(self.tab_custom_reports, text="Reportes personalizados")
        self._construir_tab_graficos_dinamicos(card_bg)
        self._construir_tab_reportes_personalizados(card_bg)

    def _builder_card(self, parent, title, subtitle, card_bg):
        card = tk.Frame(parent, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        header = tk.Frame(card, bg=card_bg)
        header.pack(fill=tk.X, padx=12, pady=(10, 6))
        tk.Label(header, text=title, font=("Segoe UI", 11, "bold"), bg=card_bg, fg=self.C["text"]).pack(anchor="w")
        if subtitle:
            tk.Label(header, text=subtitle, font=("Segoe UI", 8), bg=card_bg, fg=self.C.get("muted", "#64748B"), wraplength=310, justify="left").pack(anchor="w", pady=(2, 0))
        body = tk.Frame(card, bg=card_bg)
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        return card, body

    def _scrollable_builder_card(self, parent, title, subtitle, card_bg, width):
        host = tk.Frame(parent, bg=self.C["bg"], width=width)
        host.pack_propagate(False)

        card = tk.Frame(host, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        header = tk.Frame(card, bg=card_bg)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        tk.Label(header, text=title, font=("Segoe UI", 11, "bold"), bg=card_bg, fg=self.C["text"]).pack(anchor="w")
        if subtitle:
            tk.Label(header, text=subtitle, font=("Segoe UI", 8), bg=card_bg, fg=self.C.get("muted", "#64748B"), wraplength=310, justify="left").pack(anchor="w", pady=(2, 0))

        scroll_wrap = tk.Frame(card, bg=card_bg)
        scroll_wrap.grid(row=1, column=0, sticky="nsew", padx=(10, 6), pady=(0, 10))
        scroll_wrap.grid_columnconfigure(0, weight=1)
        scroll_wrap.grid_rowconfigure(0, weight=1)

        canvas = tk.Canvas(scroll_wrap, bg=card_bg, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(scroll_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        shell = tk.Frame(canvas, bg=card_bg)
        body = tk.Frame(shell, bg=card_bg)
        body.pack(fill=tk.BOTH, expand=True, padx=(0, 2), pady=(0, 2))
        window_id = canvas.create_window((0, 0), window=shell, anchor="nw")

        shell.bind("<Configure>", lambda _e, c=canvas: c.configure(scrollregion=c.bbox("all")))
        canvas.bind("<Configure>", lambda e, c=canvas, item=window_id: c.itemconfigure(item, width=max(e.width - 2, 1)))
        return host, body, canvas

    def _target_builder_width(self, paned, ratio, min_width, max_width):
        total = max(paned.winfo_width(), paned.winfo_reqwidth(), max_width)
        return max(min_width, min(max_width, int(total * ratio)))

    def _create_collapsible_section(self, parent, title, bg, default_open=False, note="", button_below=False):
        card = tk.Frame(parent, bg=bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        card.pack(fill=tk.X, pady=(8, 0))

        head = tk.Frame(card, bg=bg)
        head.pack(fill=tk.X, padx=10, pady=(8, 6))

        labels = tk.Frame(head, bg=bg)
        if button_below:
            labels.pack(fill=tk.X)
        else:
            labels.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(labels, text=title, font=("Segoe UI", 8, "bold"), bg=bg, fg=self.C["text"]).pack(anchor="w")
        if note:
            tk.Label(labels, text=note, font=("Segoe UI", 8), bg=bg, fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(1, 0))

        body = tk.Frame(card, bg=bg)
        state = {"open": default_open, "body": body, "button": None}
        button = ttk.Button(head, text="", width=12, command=lambda s=state: self._toggle_collapsible_section(s))
        if button_below:
            button.pack(fill=tk.X, pady=(6, 0))
        else:
            button.pack(side=tk.RIGHT)
        state["button"] = button
        self._toggle_collapsible_section(state, initial=True)
        return body, state

    def _toggle_collapsible_section(self, state, initial=False):
        if not initial:
            state["open"] = not state["open"]
        if state["open"]:
            state["body"].pack(fill=tk.X, padx=10, pady=(0, 8))
        else:
            state["body"].pack_forget()
        if state.get("button") is not None:
            state["button"].config(text="Ocultar" if state["open"] else "Mostrar")

    def _set_status_label(self, label, text, tone="muted"):
        palette = {
            "muted": self.C.get("muted", "#64748B"),
            "success": self.C.get("secondary", "#0F766E"),
            "danger": self.C.get("danger", "#DC2626"),
        }
        label.config(text=text, fg=palette.get(tone, palette["muted"]))

    def _field_block(self, parent, title):
        frame = tk.Frame(parent, bg=parent["bg"])
        frame.pack(fill=tk.X, pady=3)
        tk.Label(frame, text=title, font=("Segoe UI", 8, "bold"), bg=parent["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 3))
        return frame

    def _crear_builder_filtros_dinamicos(self, parent, scope):
        state = {"field_var": tk.StringVar(value=""), "operator_var": tk.StringVar(value=""), "value_var": tk.StringVar(value="")}
        container = tk.Frame(parent, bg=parent["bg"])
        container.pack(fill=tk.X, pady=(8, 2))

        field_box = self._field_block(container, "Filtro adicional")
        state["field_combo"] = ttk.Combobox(field_box, state="readonly", textvariable=state["field_var"])
        state["field_combo"].pack(fill=tk.X)
        state["field_combo"].bind("<<ComboboxSelected>>", lambda _e, name=scope: self._on_dynamic_filter_field_change(name))

        row = tk.Frame(container, bg=container["bg"])
        row.pack(fill=tk.X, pady=4)
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)

        op_box = tk.Frame(row, bg=row["bg"])
        op_box.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        tk.Label(op_box, text="Condicion", font=("Segoe UI", 8, "bold"), bg=row["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 4))
        state["operator_combo"] = ttk.Combobox(op_box, state="readonly", textvariable=state["operator_var"])
        state["operator_combo"].pack(fill=tk.X)

        val_box = tk.Frame(row, bg=row["bg"])
        val_box.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        tk.Label(val_box, text="Valor", font=("Segoe UI", 8, "bold"), bg=row["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 4))
        state["value_combo"] = ttk.Combobox(val_box, textvariable=state["value_var"])
        state["value_combo"].pack(fill=tk.X)

        btns = tk.Frame(container, bg=container["bg"])
        btns.pack(fill=tk.X, pady=(4, 4))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        ttk.Button(btns, text="Agregar filtro", command=lambda name=scope: self._agregar_filtro_dinamico(name)).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(btns, text="Quitar", command=lambda name=scope: self._quitar_filtro_dinamico(name)).grid(row=1, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(btns, text="Limpiar", command=lambda name=scope: self._limpiar_filtros_dinamicos(name)).grid(row=1, column=1, sticky="ew", padx=(4, 0))

        list_box = self._field_block(container, "Filtros activos")
        list_wrap = tk.Frame(list_box, bg=list_box["bg"])
        list_wrap.pack(fill=tk.BOTH, expand=True)
        state["listbox"] = tk.Listbox(list_wrap, activestyle="none", selectmode=tk.SINGLE, exportselection=False)
        list_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=state["listbox"].yview)
        state["listbox"].configure(yscrollcommand=list_scroll.set)
        state["listbox"].pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.dynamic_filter_builders[scope] = state

    def _on_dynamic_filter_field_change(self, scope):
        state = self.dynamic_filter_builders.get(scope) or {}
        fields, _by_key, label_map = self._dynamic_fields(scope)
        field_key = label_map.get(state.get("field_var").get(), "")
        meta = next((field for field in fields if field["key"] == field_key), None)
        if not meta:
            state.get("operator_combo").configure(values=())
            state.get("value_combo").configure(values=(), state="normal")
            state.get("operator_var").set("")
            state.get("value_var").set("")
            return
        operators = list(meta.get("filter_ops") or [])
        state.get("operator_combo").configure(values=operators)
        state.get("operator_var").set(operators[0] if operators else "")
        choices = list(meta.get("choices") or [])
        combo_state = "readonly" if choices else "normal"
        state.get("value_combo").configure(values=choices, state=combo_state)
        state.get("value_var").set("")

    def _refresh_dynamic_filter_builder(self, scope):
        state = self.dynamic_filter_builders.get(scope) or {}
        fields, _by_key, _label_map = self._dynamic_fields(scope)
        labels = [field["label"] for field in fields]
        state.get("field_combo").configure(values=labels)
        if state.get("field_var").get() not in labels:
            state.get("field_var").set(labels[0] if labels else "")
        self._on_dynamic_filter_field_change(scope)
        self._render_dynamic_filters_list(scope)

    def _render_dynamic_filters_list(self, scope):
        state = self.dynamic_filter_builders.get(scope) or {}
        _fields, by_key, _label_map = self._dynamic_fields(scope)
        listbox = state.get("listbox")
        if listbox is None:
            return
        listbox.delete(0, tk.END)
        for item in self.dynamic_filters.get(scope, []):
            meta = by_key.get(item.get("field")) or {}
            listbox.insert(tk.END, f"{meta.get('label') or item.get('field')} {item.get('operator')} {item.get('value')}")

    def _agregar_filtro_dinamico(self, scope):
        state = self.dynamic_filter_builders.get(scope) or {}
        _fields, _by_key, label_map = self._dynamic_fields(scope)
        field_label = state.get("field_var").get().strip()
        operator = state.get("operator_var").get().strip()
        value = state.get("value_var").get().strip()
        field_key = label_map.get(field_label, "")
        if not field_key or not operator:
            messagebox.showwarning("Filtro incompleto", "Selecciona el campo y la condicion del filtro adicional.", parent=self.win)
            return
        if operator not in {"Vacio", "Con valor"} and not value:
            messagebox.showwarning("Filtro incompleto", "Ingresa un valor para el filtro adicional.", parent=self.win)
            return
        self.dynamic_filters.setdefault(scope, []).append({"field": field_key, "operator": operator, "value": value})
        state.get("value_var").set("")
        self._render_dynamic_filters_list(scope)

    def _quitar_filtro_dinamico(self, scope):
        state = self.dynamic_filter_builders.get(scope) or {}
        listbox = state.get("listbox")
        if listbox is None or not listbox.curselection():
            return
        index = listbox.curselection()[0]
        filtros = self.dynamic_filters.get(scope, [])
        if 0 <= index < len(filtros):
            filtros.pop(index)
        self._render_dynamic_filters_list(scope)

    def _limpiar_filtros_dinamicos(self, scope):
        self.dynamic_filters[scope] = []
        self._render_dynamic_filters_list(scope)

    def _construir_tab_graficos_dinamicos(self, card_bg):
        outer = tk.Frame(self.tab_dynamic_charts, bg=self.C["bg"])
        outer.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        if not self._perm("ver_graficos"):
            aviso = tk.Frame(self.tab_dynamic_charts, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
            aviso.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            tk.Label(aviso, text="No tienes permiso para ver graficos dinamicos.", font=("Segoe UI", 11, "bold"), bg=card_bg, fg=self.C["text"]).pack(anchor="w", padx=20, pady=(18, 4))
            tk.Label(aviso, text="Puedes seguir usando los reportes personalizados y las exportaciones del Centro BI.", font=("Segoe UI", 9), bg=card_bg, fg=self.C.get("muted", "#64748B")).pack(anchor="w", padx=20, pady=(0, 18))
            return

        self.chart_paned = ttk.Panedwindow(outer, orient=tk.HORIZONTAL)
        self.chart_paned.pack(fill=tk.BOTH, expand=True)
        self.tab_dynamic_charts.bind("<Map>", lambda _e: self._programar_sync_chart_builder())
        self.chart_paned.bind("<Configure>", lambda _e: self._ajustar_ancho_chart_builder())
        self.chart_paned.bind("<ButtonRelease-1>", lambda _e: self._programar_sync_chart_builder())

        self.frm_chart_builder_host, left_body, _chart_canvas = self._scrollable_builder_card(
            self.chart_paned,
            "Constructor",
            "",
            card_bg,
            self.chart_builder_width,
        )

        self.frm_chart_visual_host = tk.Frame(self.chart_paned, bg=self.C["bg"])
        self.chart_paned.add(self.frm_chart_builder_host, weight=1)
        self.chart_paned.add(self.frm_chart_visual_host, weight=3)

        tk.Label(left_body, text="Basico", font=("Segoe UI", 8, "bold"), bg=left_body["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 4))

        source_box = self._field_block(left_body, "Fuente")
        self.cb_chart_source = ttk.Combobox(source_box, state="readonly", values=[self.dynamic_source_labels[key] for key in self.dynamic_source_keys], textvariable=self.var_chart_source)
        self.cb_chart_source.pack(fill=tk.X)
        self.cb_chart_source.bind("<<ComboboxSelected>>", lambda _e: self._actualizar_form_grafico_dinamico())

        x_box = self._field_block(left_body, "Eje X")
        self.cb_chart_x = ttk.Combobox(x_box, state="readonly", textvariable=self.var_chart_x)
        self.cb_chart_x.pack(fill=tk.X)

        y_box = self._field_block(left_body, "Eje Y")
        self.cb_chart_y = ttk.Combobox(y_box, state="readonly", textvariable=self.var_chart_y)
        self.cb_chart_y.pack(fill=tk.X)

        type_box = self._field_block(left_body, "Visual")
        self.cb_chart_type = ttk.Combobox(type_box, state="readonly", values=CHART_TYPE_OPTIONS, textvariable=self.var_chart_type)
        self.cb_chart_type.pack(fill=tk.X)

        chart_adv_body, _chart_adv_state = self._create_collapsible_section(
            left_body,
            "Opciones avanzadas",
            left_body["bg"],
            default_open=self.chart_advanced_open,
            note="Agregacion, rango visible y filtros adicionales.",
            button_below=True,
        )

        row = tk.Frame(chart_adv_body, bg=chart_adv_body["bg"])
        row.pack(fill=tk.X, pady=(0, 2))
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        agg_box = tk.Frame(row, bg=row["bg"])
        agg_box.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        tk.Label(agg_box, text="Agregacion", font=("Segoe UI", 8, "bold"), bg=row["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 3))
        self.cb_chart_agg = ttk.Combobox(agg_box, state="readonly", values=AGGREGATION_OPTIONS, textvariable=self.var_chart_agg)
        self.cb_chart_agg.pack(fill=tk.X)

        limit_box = tk.Frame(row, bg=row["bg"])
        limit_box.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        tk.Label(limit_box, text="Top / rango", font=("Segoe UI", 8, "bold"), bg=row["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 3))
        self.cb_chart_limit = ttk.Combobox(limit_box, state="readonly", values=CHART_LIMIT_OPTIONS, textvariable=self.var_chart_limit)
        self.cb_chart_limit.pack(fill=tk.X)

        self._crear_builder_filtros_dinamicos(chart_adv_body, "chart")

        chart_btns = tk.Frame(left_body, bg=left_body["bg"])
        chart_btns.pack(fill=tk.X, pady=(10, 0))
        chart_btns.columnconfigure(0, weight=1)
        chart_btns.columnconfigure(1, weight=1)
        ttk.Button(chart_btns, text="Generar grafico", command=self._generar_grafico_dinamico).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(chart_btns, text="Exportar grafico", command=self._exportar_grafico_dinamico).grid(row=1, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(chart_btns, text="Limpiar seleccion", command=self._limpiar_grafico_dinamico).grid(row=1, column=1, sticky="ew", padx=(4, 0))

        self.lbl_chart_status = tk.Label(left_body, text="", font=("Segoe UI", 8), bg=left_body["bg"], fg=self.C.get("muted", "#64748B"), wraplength=330, justify="left")
        self.lbl_chart_status.pack(fill=tk.X, pady=(8, 0))

        right = self.frm_chart_visual_host
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=7)
        right.rowconfigure(2, weight=3)

        head = tk.Frame(right, bg=self.C["bg"])
        head.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        head.columnconfigure(0, weight=1)
        title_wrap = tk.Frame(head, bg=self.C["bg"])
        title_wrap.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        self.lbl_dynamic_chart_title = tk.Label(title_wrap, text="Grafico dinamico", font=("Segoe UI", 14, "bold"), bg=self.C["bg"], fg=self.C["text"])
        self.lbl_dynamic_chart_title.pack(anchor="w")
        self.lbl_dynamic_chart_meta = tk.Label(title_wrap, text="", font=("Segoe UI", 8, "bold"), bg=self.C["bg"], fg=self.C.get("secondary", "#0F766E"))
        self.lbl_dynamic_chart_meta.pack(anchor="w", pady=(2, 0))
        self.lbl_dynamic_chart_subtitle = tk.Label(title_wrap, text="El grafico se expande para priorizar la visualizacion.", font=("Segoe UI", 8), bg=self.C["bg"], fg=self.C.get("muted", "#64748B"), wraplength=920, justify="left")
        self.lbl_dynamic_chart_subtitle.pack(anchor="w", pady=(2, 0))
        head.columnconfigure(1, minsize=230)
        actions = tk.Frame(head, bg=self.C["bg"], width=230)
        actions.grid(row=0, column=1, sticky="e", padx=(8, 0), pady=2)
        actions.grid_propagate(False)
        self.btn_toggle_chart_builder = ttk.Button(actions, text="Ocultar constructor", width=24, command=self._toggle_chart_builder_panel)
        self.btn_toggle_chart_builder.pack(side=tk.RIGHT, fill=tk.X)

        chart_card = tk.Frame(right, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        chart_card.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        chart_card.grid_columnconfigure(0, weight=1)
        chart_card.grid_rowconfigure(0, weight=1)
        chart_card.configure(height=430)
        chart_card.grid_propagate(False)
        self.frm_dynamic_chart_plot = tk.Frame(chart_card, bg=card_bg)
        self.frm_dynamic_chart_plot.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.frm_dynamic_chart_plot.bind("<Configure>", self._on_dynamic_chart_plot_resize)

        table_card = tk.Frame(right, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        table_card.grid(row=2, column=0, sticky="nsew")
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(1, weight=1)
        table_card.configure(height=280)
        table_card.grid_propagate(False)
        self.frm_dynamic_chart_summary = tk.Frame(table_card, bg=card_bg)
        self.frm_dynamic_chart_summary.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        table_wrap = tk.Frame(table_card, bg=card_bg)
        table_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_wrap.grid_columnconfigure(0, weight=1)
        table_wrap.grid_rowconfigure(0, weight=1)
        self.tree_dynamic_chart = ttk.Treeview(table_wrap, show="headings")
        sb_y = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree_dynamic_chart.yview)
        sb_x = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree_dynamic_chart.xview)
        self.tree_dynamic_chart.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        self.tree_dynamic_chart.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        bloquear_columnas(self.tree_dynamic_chart)

        self._actualizar_form_grafico_dinamico()
        self._aplicar_estado_chart_builder()
        self._programar_sync_chart_builder()

    def _ajustar_ancho_chart_builder(self):
        if not hasattr(self, "chart_paned") or self.chart_builder_collapsed:
            return
        self.frm_chart_builder_host.configure(width=self.chart_builder_width)
        try:
            self.chart_paned.sashpos(0, self.chart_builder_width)
        except Exception:
            pass

    def _programar_sync_chart_builder(self):
        if not hasattr(self, "tab_dynamic_charts"):
            return
        self.tab_dynamic_charts.after(30, self._sincronizar_chart_builder_visible)
        self.tab_dynamic_charts.after(180, self._sincronizar_chart_builder_visible)

    def _sincronizar_chart_builder_visible(self):
        if not hasattr(self, "chart_paned") or self.chart_builder_collapsed:
            return
        panes = tuple(str(pane) for pane in self.chart_paned.panes())
        builder_name = str(self.frm_chart_builder_host)
        if builder_name not in panes:
            self.chart_paned.insert(0, self.frm_chart_builder_host, weight=1)
        try:
            self.chart_paned.update_idletasks()
            self.frm_chart_builder_host.update_idletasks()
        except Exception:
            return
        self._ajustar_ancho_chart_builder()
        self._chart_builder_synced = True

    def _aplicar_estado_chart_builder(self):
        if not hasattr(self, "chart_paned") or not hasattr(self, "frm_chart_builder_host"):
            return
        panes = tuple(str(pane) for pane in self.chart_paned.panes())
        builder_name = str(self.frm_chart_builder_host)
        if self.chart_builder_collapsed:
            if builder_name in panes:
                self.chart_paned.forget(self.frm_chart_builder_host)
        else:
            if builder_name not in panes:
                self.chart_paned.insert(0, self.frm_chart_builder_host, weight=1)
            self._programar_sync_chart_builder()
        if hasattr(self, "btn_toggle_chart_builder"):
            self.btn_toggle_chart_builder.config(text="Mostrar constructor" if self.chart_builder_collapsed else "Ocultar constructor")

    def _toggle_chart_builder_panel(self):
        self.chart_builder_collapsed = not self.chart_builder_collapsed
        self._aplicar_estado_chart_builder()

    def _aplicar_estado_report_builder(self):
        if not hasattr(self, "report_paned") or not hasattr(self, "frm_report_builder_host"):
            return
        panes = tuple(str(pane) for pane in self.report_paned.panes())
        builder_name = str(self.frm_report_builder_host)
        if self.report_builder_collapsed:
            if builder_name in panes:
                self.report_paned.forget(self.frm_report_builder_host)
        else:
            if builder_name not in panes:
                self.report_paned.insert(0, self.frm_report_builder_host, weight=1)
            self._programar_sync_report_builder()
        if hasattr(self, "btn_toggle_report_builder"):
            self.btn_toggle_report_builder.config(text="Personalizar reporte" if self.report_builder_collapsed else "Ocultar configuracion")

    def _toggle_report_builder_panel(self):
        self.report_builder_collapsed = not self.report_builder_collapsed
        self._aplicar_estado_report_builder()

    def _actualizar_resumen_columnas_reporte(self):
        if not hasattr(self, "list_report_columns"):
            return
        total = self.list_report_columns.size()
        selected = len(self.list_report_columns.curselection())
        if hasattr(self, "lbl_report_columns_summary"):
            self.lbl_report_columns_summary.config(text=f"{selected} de {total} columnas seleccionadas")
        if hasattr(self, "lbl_custom_report_meta"):
            fuente = self.var_report_source.get().strip() or "Fuente"
            self.lbl_custom_report_meta.config(text=f"{fuente} | {selected} columnas")

    def _seleccionar_todas_columnas_reporte(self):
        if not hasattr(self, "list_report_columns"):
            return
        self.list_report_columns.selection_set(0, tk.END)
        self._actualizar_resumen_columnas_reporte()

    def _limpiar_columnas_reporte(self):
        if not hasattr(self, "list_report_columns"):
            return
        self.list_report_columns.selection_clear(0, tk.END)
        self._actualizar_resumen_columnas_reporte()

    def _construir_tab_reportes_personalizados(self, card_bg):
        outer = tk.Frame(self.tab_custom_reports, bg=self.C["bg"])
        outer.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.report_paned = ttk.Panedwindow(outer, orient=tk.HORIZONTAL)
        self.report_paned.pack(fill=tk.BOTH, expand=True)
        self.tab_custom_reports.bind("<Map>", lambda _e: self._programar_sync_report_builder())
        self.report_paned.bind("<Configure>", lambda _e: self._ajustar_ancho_report_builder())
        self.report_paned.bind("<ButtonRelease-1>", lambda _e: self._programar_sync_report_builder())

        self.frm_report_builder_host, left_body, _report_canvas = self._scrollable_builder_card(
            self.report_paned,
            "Personalizar reporte",
            "",
            card_bg,
            self.report_builder_width,
        )

        self.frm_report_preview_host = tk.Frame(self.report_paned, bg=self.C["bg"])
        self.report_paned.add(self.frm_report_builder_host, weight=1)
        self.report_paned.add(self.frm_report_preview_host, weight=3)

        tk.Label(left_body, text="Basico", font=("Segoe UI", 8, "bold"), bg=left_body["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 4))

        source_box = self._field_block(left_body, "Fuente")
        self.cb_report_source = ttk.Combobox(source_box, state="readonly", values=[self.dynamic_source_labels[key] for key in self.dynamic_source_keys], textvariable=self.var_report_source)
        self.cb_report_source.pack(fill=tk.X)
        self.cb_report_source.bind("<<ComboboxSelected>>", lambda _e: self._actualizar_form_reporte_dinamico())

        cols_body, _report_cols_state = self._create_collapsible_section(
            left_body,
            "Columnas visibles",
            left_body["bg"],
            default_open=self.report_columns_open,
            note="Selecciona solo lo que quieres ver y exportar.",
        )
        cols_head = tk.Frame(cols_body, bg=cols_body["bg"])
        cols_head.pack(fill=tk.X, pady=(0, 4))
        cols_head.columnconfigure(0, weight=1)
        self.lbl_report_columns_summary = tk.Label(cols_head, text="", font=("Segoe UI", 8), bg=cols_body["bg"], fg=self.C.get("muted", "#64748B"))
        self.lbl_report_columns_summary.grid(row=0, column=0, sticky="w")
        cols_actions = tk.Frame(cols_head, bg=cols_body["bg"])
        cols_actions.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        cols_actions.columnconfigure(0, weight=1)
        cols_actions.columnconfigure(1, weight=1)
        ttk.Button(cols_actions, text="Todas", command=self._seleccionar_todas_columnas_reporte).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(cols_actions, text="Limpiar", command=self._limpiar_columnas_reporte).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        cols_wrap = tk.Frame(cols_body, bg=cols_body["bg"])
        cols_wrap.pack(fill=tk.BOTH, expand=True)
        self.list_report_columns = tk.Listbox(cols_wrap, selectmode=tk.MULTIPLE, exportselection=False)
        cols_scroll = ttk.Scrollbar(cols_wrap, orient="vertical", command=self.list_report_columns.yview)
        self.list_report_columns.configure(yscrollcommand=cols_scroll.set)
        self.list_report_columns.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cols_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_report_columns.bind("<<ListboxSelect>>", lambda _e: self._actualizar_resumen_columnas_reporte())

        advanced_body, _report_adv_state = self._create_collapsible_section(
            left_body,
            "Opciones avanzadas",
            left_body["bg"],
            default_open=self.report_advanced_open,
            note="Orden, subtotales, resumen y filtros adicionales.",
        )

        row = tk.Frame(advanced_body, bg=advanced_body["bg"])
        row.pack(fill=tk.X, pady=(0, 2))
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        sort_box = tk.Frame(row, bg=row["bg"])
        sort_box.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        tk.Label(sort_box, text="Ordenar por", font=("Segoe UI", 8, "bold"), bg=row["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 4))
        self.cb_report_sort = ttk.Combobox(sort_box, state="readonly", textvariable=self.var_report_sort)
        self.cb_report_sort.pack(fill=tk.X)

        subtotal_box = tk.Frame(row, bg=row["bg"])
        subtotal_box.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        tk.Label(subtotal_box, text="Subtotal por", font=("Segoe UI", 8, "bold"), bg=row["bg"], fg=self.C.get("muted", "#64748B")).pack(anchor="w", pady=(0, 4))
        self.cb_report_subtotal = ttk.Combobox(subtotal_box, state="readonly", textvariable=self.var_report_subtotal)
        self.cb_report_subtotal.pack(fill=tk.X)

        opts = tk.Frame(advanced_body, bg=advanced_body["bg"])
        opts.pack(fill=tk.X, pady=(6, 2))
        ttk.Radiobutton(opts, text="Ascendente", value="asc", variable=self.var_report_sort_dir).pack(anchor="w")
        ttk.Radiobutton(opts, text="Descendente", value="desc", variable=self.var_report_sort_dir).pack(anchor="w")
        ttk.Checkbutton(opts, text="Mostrar resumen", variable=self.var_report_summary).pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(opts, text="Mostrar totales", variable=self.var_report_totals).pack(anchor="w")
        ttk.Checkbutton(opts, text="Mostrar subtotales", variable=self.var_report_subtotals).pack(anchor="w")

        self._crear_builder_filtros_dinamicos(advanced_body, "report")

        btns = tk.Frame(left_body, bg=left_body["bg"])
        btns.pack(fill=tk.X, pady=(10, 0))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        ttk.Button(btns, text="Previsualizar", command=self._previsualizar_reporte_personalizado).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        self.btn_dynamic_report_pdf = ttk.Button(btns, text="Exportar PDF", command=self._exportar_reporte_personalizado_pdf)
        self.btn_dynamic_report_pdf.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        self.btn_dynamic_report_excel = ttk.Button(btns, text="Exportar Excel", command=self._exportar_reporte_personalizado_excel)
        self.btn_dynamic_report_excel.grid(row=1, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(btns, text="Limpiar", command=self._limpiar_reporte_personalizado).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        self.lbl_report_status = tk.Label(left_body, text="", font=("Segoe UI", 8), bg=left_body["bg"], fg=self.C.get("muted", "#64748B"), wraplength=330, justify="left")
        self.lbl_report_status.pack(fill=tk.X, pady=(8, 0))

        right = self.frm_report_preview_host
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        head = tk.Frame(right, bg=self.C["bg"])
        head.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        head.columnconfigure(0, weight=1)
        title_wrap = tk.Frame(head, bg=self.C["bg"])
        title_wrap.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        self.lbl_custom_report_title = tk.Label(title_wrap, text="Reporte personalizado", font=("Segoe UI", 14, "bold"), bg=self.C["bg"], fg=self.C["text"])
        self.lbl_custom_report_title.pack(anchor="w")
        self.lbl_custom_report_meta = tk.Label(title_wrap, text="", font=("Segoe UI", 8, "bold"), bg=self.C["bg"], fg=self.C.get("secondary", "#0F766E"))
        self.lbl_custom_report_meta.pack(anchor="w", pady=(2, 0))
        self.lbl_custom_report_subtitle = tk.Label(title_wrap, text="La vista previa ocupa el foco principal y la configuracion queda al costado.", font=("Segoe UI", 8), bg=self.C["bg"], fg=self.C.get("muted", "#64748B"), wraplength=920, justify="left")
        self.lbl_custom_report_subtitle.pack(anchor="w", pady=(2, 0))
        head.columnconfigure(1, minsize=190)
        actions = tk.Frame(head, bg=self.C["bg"], width=190)
        actions.grid(row=0, column=1, sticky="e", padx=(8, 0), pady=2)
        actions.grid_propagate(False)
        self.btn_toggle_report_builder = ttk.Button(actions, text="Ocultar configuracion", width=20, command=self._toggle_report_builder_panel)
        self.btn_toggle_report_builder.pack(side=tk.RIGHT, fill=tk.X)

        preview_card = tk.Frame(right, bg=card_bg, highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
        preview_card.grid(row=1, column=0, sticky="nsew")
        preview_card.grid_columnconfigure(0, weight=1)
        preview_card.grid_rowconfigure(1, weight=1)
        preview_card.configure(height=620)
        preview_card.grid_propagate(False)
        self.frm_custom_report_summary = tk.Frame(preview_card, bg=card_bg)
        self.frm_custom_report_summary.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        table_wrap = tk.Frame(preview_card, bg=card_bg)
        table_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_wrap.grid_columnconfigure(0, weight=1)
        table_wrap.grid_rowconfigure(0, weight=1)
        self.tree_custom_report = ttk.Treeview(table_wrap, show="headings")
        sb_y = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree_custom_report.yview)
        sb_x = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree_custom_report.xview)
        self.tree_custom_report.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        self.tree_custom_report.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        bloquear_columnas(self.tree_custom_report)

        self._actualizar_form_reporte_dinamico()
        self._aplicar_estado_report_builder()
        self._programar_sync_report_builder()

    def _ajustar_ancho_report_builder(self):
        if not hasattr(self, "report_paned"):
            return
        if self.report_builder_collapsed:
            return
        self.frm_report_builder_host.configure(width=self.report_builder_width)
        try:
            self.report_paned.sashpos(0, self.report_builder_width)
        except Exception:
            pass

    def _programar_sync_report_builder(self):
        if not hasattr(self, "tab_custom_reports"):
            return
        self.tab_custom_reports.after(30, self._sincronizar_report_builder_visible)
        self.tab_custom_reports.after(180, self._sincronizar_report_builder_visible)

    def _sincronizar_report_builder_visible(self):
        if not hasattr(self, "report_paned") or self.report_builder_collapsed:
            return
        panes = tuple(str(pane) for pane in self.report_paned.panes())
        builder_name = str(self.frm_report_builder_host)
        if builder_name not in panes:
            self.report_paned.insert(0, self.frm_report_builder_host, weight=1)
        try:
            self.report_paned.update_idletasks()
            self.frm_report_builder_host.update_idletasks()
        except Exception:
            return
        self._ajustar_ancho_report_builder()
        self._report_builder_synced = True

    def _on_dynamic_chart_plot_resize(self, _event=None):
        if not getattr(self, "grafico_dinamico_actual", None):
            return
        size = (
            max(int(getattr(_event, "width", 0) or self.frm_dynamic_chart_plot.winfo_width() or 0), 0),
            max(int(getattr(_event, "height", 0) or self.frm_dynamic_chart_plot.winfo_height() or 0), 0),
        )
        if size[0] < 80 or size[1] < 80 or size == self._dynamic_chart_plot_size:
            return
        self._dynamic_chart_plot_size = size
        if self._dynamic_chart_resize_after:
            try:
                self.win.after_cancel(self._dynamic_chart_resize_after)
            except Exception:
                pass
        self._dynamic_chart_resize_after = self.win.after(180, self._redibujar_grafico_dinamico_actual)

    def _redibujar_grafico_dinamico_actual(self):
        self._dynamic_chart_resize_after = None
        if not getattr(self, "grafico_dinamico_actual", None) or not hasattr(self, "frm_dynamic_chart_plot"):
            return
        self._limpiar_canvases("dynamic_chart")
        self._limpiar_panel_chart(self.frm_dynamic_chart_plot)
        self._render_dynamic_chart(self.frm_dynamic_chart_plot, self.grafico_dinamico_actual, group="dynamic_chart")

    def _actualizar_form_grafico_dinamico(self):
        fields, _by_key, _label_map = self._dynamic_fields("chart")
        x_labels = [field["label"] for field in fields if field.get("chart_x")]
        y_labels = [field["label"] for field in fields if field.get("chart_y")]
        source = self._dynamic_source("chart")
        default_chart = source.get("default_chart") or {}
        default_x = next((field["label"] for field in fields if field["key"] == default_chart.get("x_field")), x_labels[0] if x_labels else "")
        default_y = next((field["label"] for field in fields if field["key"] == default_chart.get("y_field")), y_labels[0] if y_labels else "")
        self.cb_chart_x.configure(values=x_labels)
        self.cb_chart_y.configure(values=y_labels)
        self.var_chart_x.set(default_x if self.var_chart_x.get() not in x_labels else self.var_chart_x.get())
        self.var_chart_y.set(default_y if self.var_chart_y.get() not in y_labels else self.var_chart_y.get())
        self.var_chart_agg.set(default_chart.get("aggregation", self.var_chart_agg.get() or "Suma"))
        self.var_chart_type.set(default_chart.get("chart_type", self.var_chart_type.get() or "Barras verticales"))
        self.var_chart_limit.set(default_chart.get("limit", self.var_chart_limit.get() or "Top 10"))
        self._refresh_dynamic_filter_builder("chart")
        if hasattr(self, "lbl_dynamic_chart_meta"):
            self.lbl_dynamic_chart_meta.config(text=f"{self.var_chart_source.get() or 'Fuente'} | {self.var_chart_x.get() or 'X'} vs {self.var_chart_y.get() or 'Y'}")
        if hasattr(self, "lbl_dynamic_chart_subtitle"):
            self.lbl_dynamic_chart_subtitle.config(text=source.get("description") or "Selecciona campos compatibles y genera la vista.")
        self._set_status_label(self.lbl_chart_status, source.get("description") or "Configuracion lista para generar.")

    def _actualizar_form_reporte_dinamico(self):
        fields, _by_key, _label_map = self._dynamic_fields("report")
        field_labels = [field["label"] for field in fields]
        default_columns = set(self._dynamic_source("report").get("default_columns") or [])
        self.list_report_columns.delete(0, tk.END)
        for idx, field in enumerate(fields):
            self.list_report_columns.insert(tk.END, field["label"])
            if field["key"] in default_columns or (not default_columns and field.get("default_selected")):
                self.list_report_columns.selection_set(idx)
        self.cb_report_sort.configure(values=field_labels)
        self.cb_report_subtotal.configure(values=[""] + field_labels)
        source = self._dynamic_source("report")
        default_sort = next((field["label"] for field in fields if field["key"] == source.get("default_sort_field")), field_labels[0] if field_labels else "")
        self.var_report_sort.set(default_sort)
        if self.var_report_subtotal.get() not in [""] + field_labels:
            self.var_report_subtotal.set("")
        self._refresh_dynamic_filter_builder("report")
        self._actualizar_resumen_columnas_reporte()
        self._actualizar_estado_exportacion_personalizada()
        if hasattr(self, "lbl_custom_report_subtitle"):
            self.lbl_custom_report_subtitle.config(text=source.get("description") or "Selecciona columnas y previsualiza para enfocar la salida.")
        self._set_status_label(self.lbl_report_status, source.get("description") or "Configuracion lista para previsualizar.")

    def _pintar_resumen_dinamico(self, parent, summary):
        for child in parent.winfo_children():
            child.destroy()
        items = list((summary or {}).items())
        if not items:
            return
        cols = min(5, max(1, len(items)))
        for col in range(cols):
            parent.columnconfigure(col, weight=1)
        for idx, (label, value) in enumerate(items):
            card = tk.Frame(parent, bg="#F8FAFC", highlightbackground=self.C.get("border", "#E2E8F0"), highlightthickness=1)
            card.grid(row=idx // cols, column=idx % cols, sticky="ew", padx=4, pady=4)
            tk.Label(card, text=str(label), font=("Segoe UI", 8, "bold"), bg="#F8FAFC", fg=self.C.get("muted", "#64748B"), wraplength=160, justify="left").pack(anchor="w", padx=8, pady=(6, 1))
            tk.Label(card, text=self._mostrar_valor(value, "currency" if isinstance(value, float) else None), font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg=self.C["text"], wraplength=160, justify="left").pack(anchor="w", padx=8, pady=(0, 7))

    def _render_dynamic_tree(self, tree, columns, rows, formats):
        tree.delete(*tree.get_children())
        tree.configure(columns=columns)
        for col in columns:
            fmt = (formats or {}).get(col)
            anchor = "e" if fmt in {"currency", "number", "percent"} else "w"
            max_len = len(col)
            for row in list(rows or [])[:40]:
                text = self._mostrar_valor(row.get(col), fmt)
                max_len = max(max_len, max((len(line) for line in str(text).splitlines()), default=0))
            tree.heading(col, text=col)
            tree.column(col, width=min(max(130, max_len * 8 + 24), 320), anchor=anchor)
        for row in rows:
            values = [self._mostrar_valor(row.get(col), (formats or {}).get(col)) for col in columns]
            tree.insert("", tk.END, values=values)

    def _generar_grafico_dinamico(self):
        _fields, by_key, label_map = self._dynamic_fields("chart")
        config = {
            "source": self._dynamic_source_key("chart"),
            "x_field": label_map.get(self.var_chart_x.get(), ""),
            "y_field": label_map.get(self.var_chart_y.get(), ""),
            "aggregation": self.var_chart_agg.get(),
            "chart_type": self.var_chart_type.get(),
            "limit": self.var_chart_limit.get(),
            "extra_filters": list(self.dynamic_filters.get("chart", [])),
        }
        try:
            payload = self.db.generar_grafico_dinamico(config, self._obtener_filtros())
        except Exception as exc:
            self._limpiar_canvases("dynamic_chart")
            self._limpiar_panel_chart(self.frm_dynamic_chart_plot)
            self._render_dynamic_tree(self.tree_dynamic_chart, [], [], {})
            self._set_status_label(self.lbl_chart_status, str(exc), tone="danger")
            messagebox.showwarning("Grafico dinamico", str(exc), parent=self.win)
            return

        self.grafico_dinamico_actual = payload
        self._limpiar_canvases("dynamic_chart")
        self._limpiar_panel_chart(self.frm_dynamic_chart_plot)
        self._render_dynamic_chart(self.frm_dynamic_chart_plot, payload, group="dynamic_chart")
        self._pintar_resumen_dinamico(self.frm_dynamic_chart_summary, payload.get("summary") or {})
        self._render_dynamic_tree(self.tree_dynamic_chart, payload.get("preview_columns") or [], payload.get("preview_rows") or [], payload.get("preview_formats") or {})
        self.lbl_dynamic_chart_title.config(text=payload.get("title") or "Grafico dinamico")
        self.lbl_dynamic_chart_subtitle.config(text=payload.get("subtitle") or "")
        if hasattr(self, "lbl_dynamic_chart_meta"):
            self.lbl_dynamic_chart_meta.config(text=f"{self.var_chart_source.get() or 'Fuente'} | {len(payload.get('preview_rows') or [])} registros")
        self._set_status_label(self.lbl_chart_status, "Grafico generado correctamente.", tone="success")

    def _exportar_grafico_dinamico(self):
        if not self.grafico_dinamico_actual:
            messagebox.showwarning("Exportar grafico", "Primero debes generar el grafico antes de exportarlo.", parent=self.win)
            return

        canvas = self._canvas_for_group("dynamic_chart")
        figura = getattr(canvas, "figure", None) if canvas is not None else None
        if figura is None:
            messagebox.showwarning("Exportar grafico", "No se encontro una visualizacion lista para exportar.", parent=self.win)
            return

        titulo = (self.grafico_dinamico_actual.get("title") or "grafico_dinamico").strip().lower()
        nombre = "".join(ch if ch.isalnum() else "_" for ch in titulo).strip("_") or "grafico_dinamico"
        path = filedialog.asksaveasfilename(
            parent=self.win,
            title="Exportar grafico",
            initialfile=f"{nombre}.png",
            defaultextension=".png",
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg"),
                ("PDF", "*.pdf"),
            ],
        )
        if not path:
            return

        extension = path.rsplit(".", 1)[-1].lower() if "." in path else "png"
        save_kwargs = {"bbox_inches": "tight", "facecolor": "white"}
        if extension in {"png", "jpg", "jpeg"}:
            save_kwargs["dpi"] = 220

        try:
            figura.savefig(path, **save_kwargs)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo exportar el grafico:\n{exc}", parent=self.win)
            return

        messagebox.showinfo("Grafico exportado", f"Archivo guardado en:\n{path}", parent=self.win)

    def _limpiar_grafico_dinamico(self):
        self.dynamic_filters["chart"] = []
        self._render_dynamic_filters_list("chart")
        self._actualizar_form_grafico_dinamico()
        self.grafico_dinamico_actual = None
        self._limpiar_canvases("dynamic_chart")
        self._limpiar_panel_chart(self.frm_dynamic_chart_plot)
        self._pintar_resumen_dinamico(self.frm_dynamic_chart_summary, {})
        self._render_dynamic_tree(self.tree_dynamic_chart, [], [], {})
        self.lbl_dynamic_chart_title.config(text="Grafico dinamico")
        if hasattr(self, "lbl_dynamic_chart_meta"):
            self.lbl_dynamic_chart_meta.config(text="")
        self.lbl_dynamic_chart_subtitle.config(text="Selecciona una fuente, define los ejes y genera la visualizacion.")

    def _selected_report_columns(self):
        fields, _by_key, _label_map = self._dynamic_fields("report")
        indexes = self.list_report_columns.curselection()
        return [fields[idx]["key"] for idx in indexes if 0 <= idx < len(fields)]

    def _previsualizar_reporte_personalizado(self):
        _fields, _by_key, label_map = self._dynamic_fields("report")
        config = {
            "source": self._dynamic_source_key("report"),
            "columns": self._selected_report_columns(),
            "sort_field": label_map.get(self.var_report_sort.get(), ""),
            "sort_direction": self.var_report_sort_dir.get(),
            "subtotal_field": label_map.get(self.var_report_subtotal.get(), ""),
            "include_summary": self.var_report_summary.get(),
            "include_totals": self.var_report_totals.get(),
            "include_subtotals": self.var_report_subtotals.get(),
            "extra_filters": list(self.dynamic_filters.get("report", [])),
        }
        try:
            report = self.db.generar_reporte_personalizado(config, self._obtener_filtros())
        except Exception as exc:
            self._set_status_label(self.lbl_report_status, str(exc), tone="danger")
            messagebox.showwarning("Reporte personalizado", str(exc), parent=self.win)
            return
        self.reporte_personalizado_actual = report
        self.lbl_custom_report_title.config(text=report.get("titulo") or "Reporte personalizado")
        self.lbl_custom_report_subtitle.config(text=report.get("subtitulo") or "")
        self._pintar_resumen_dinamico(self.frm_custom_report_summary, report.get("resumen") or {})
        self._render_dynamic_tree(self.tree_custom_report, report.get("columnas") or [], report.get("filas") or [], report.get("formatos") or {})
        self._actualizar_estado_exportacion_personalizada()
        if hasattr(self, "lbl_custom_report_meta"):
            self.lbl_custom_report_meta.config(text=f"{report.get('source_label') or self.var_report_source.get() or 'Fuente'} | {len(report.get('columnas') or [])} columnas | {len(report.get('filas') or [])} filas")
        self._set_status_label(self.lbl_report_status, f"{len(report.get('filas') or [])} fila(s) listas para exportar.", tone="success")
        self._registrar_reporte_personalizado_historial("Vista previa")

    def _actualizar_estado_exportacion_personalizada(self):
        source_key = self.reporte_personalizado_actual.get("source_key") if self.reporte_personalizado_actual else self._dynamic_source_key("report")
        estado = "normal" if self._can_export_dynamic_source(source_key) else "disabled"
        if hasattr(self, "btn_dynamic_report_pdf"):
            self.btn_dynamic_report_pdf.config(state=estado)
        if hasattr(self, "btn_dynamic_report_excel"):
            self.btn_dynamic_report_excel.config(state=estado)

    def _registrar_reporte_personalizado_historial(self, formato):
        report = self.reporte_personalizado_actual or {}
        if not report:
            return
        filtros = dict(report.get("filters_export") or {})
        self.db.registrar_reporte_generado(
            "reporte_personalizado",
            report.get("titulo") or "Reporte personalizado",
            id_usuario=self.usuario.get("id"),
            username=self.usuario.get("username"),
            filtros=filtros,
            formato=formato,
            total_registros=len(report.get("filas") or []),
        )
        self._cargar_historial(self.db.obtener_historial_reportes())

    def _exportar_reporte_personalizado_pdf(self):
        if not self.reporte_personalizado_actual:
            self._previsualizar_reporte_personalizado()
        if not self.reporte_personalizado_actual:
            return
        if not self._can_export_dynamic_source(self.reporte_personalizado_actual.get("source_key")):
            messagebox.showwarning("Permiso requerido", "No tienes permiso para exportar esta fuente personalizada.", parent=self.win)
            return
        from reportes_gen.reports import ReportGenerator

        ok, msg = ReportGenerator().generar_reporte_ejecutivo(
            self.reporte_personalizado_actual,
            filtros=self.reporte_personalizado_actual.get("filters_export") or {},
            usuario=self.usuario,
            empresa_info=self._empresa_info(),
            color_hex=self.C.get("primary", "#1f4788"),
        )
        if ok:
            self._registrar_reporte_personalizado_historial("PDF")
            messagebox.showinfo("Reporte PDF", msg, parent=self.win)
        else:
            messagebox.showerror("Error", msg, parent=self.win)

    def _exportar_reporte_personalizado_excel(self):
        if not self.reporte_personalizado_actual:
            self._previsualizar_reporte_personalizado()
        if not self.reporte_personalizado_actual:
            return
        if not self._can_export_dynamic_source(self.reporte_personalizado_actual.get("source_key")):
            messagebox.showwarning("Permiso requerido", "No tienes permiso para exportar esta fuente personalizada.", parent=self.win)
            return
        from reportes_gen.export_excel import ExcelExporter

        ok, msg = ExcelExporter(db=self.db).exportar_reporte_ejecutivo(
            self.reporte_personalizado_actual,
            filtros=self.reporte_personalizado_actual.get("filters_export") or {},
            usuario=self.usuario,
            empresa_info=self._empresa_info(),
        )
        if ok:
            self._registrar_reporte_personalizado_historial("Excel")
            messagebox.showinfo("Reporte Excel", f"Guardado en:\n{msg}", parent=self.win)
        else:
            messagebox.showerror("Error", msg, parent=self.win)

    def _limpiar_reporte_personalizado(self):
        self.dynamic_filters["report"] = []
        self._render_dynamic_filters_list("report")
        self._actualizar_form_reporte_dinamico()
        self.reporte_personalizado_actual = None
        self._pintar_resumen_dinamico(self.frm_custom_report_summary, {})
        self._render_dynamic_tree(self.tree_custom_report, [], [], {})
        self.lbl_custom_report_title.config(text="Reporte personalizado")
        if hasattr(self, "lbl_custom_report_meta"):
            self.lbl_custom_report_meta.config(text=f"{self.var_report_source.get() or 'Fuente'} | {len(self._selected_report_columns())} columnas")
        self.lbl_custom_report_subtitle.config(text="Abre el panel lateral solo cuando necesites ajustar la estructura del reporte.")
        self._set_status_label(self.lbl_report_status, "")

