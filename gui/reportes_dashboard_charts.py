import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter

from gui.reportes_dashboard_config import as_float, label_limit, safe_label


class ReportesDashboardChartsMixin:
    def _canvas_for_group(self, group):
        if isinstance(getattr(self, "_canvas_charts", None), list):
            canvases = list(self._canvas_charts)
        else:
            canvases = list((getattr(self, "_canvas_charts", {}) or {}).get(group, []))
        return canvases[-1] if canvases else None

    def _limpiar_panel_chart(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def _limpiar_canvases(self, group=None):
        if isinstance(getattr(self, "_canvas_charts", None), list):
            groups = {"dashboard": list(self._canvas_charts)}
        else:
            groups = dict(getattr(self, "_canvas_charts", {}) or {})

        keys = [group] if group else list(groups.keys())
        for key in keys:
            for canvas in groups.get(key, []):
                try:
                    canvas.get_tk_widget().destroy()
                except Exception:
                    pass
            groups[key] = []

        self._canvas_charts = groups if not isinstance(getattr(self, "_canvas_charts", None), list) else []

    def _dibujar_figura(self, frame, fig, group="dashboard"):
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.configure(bg=frame["bg"], highlightthickness=0)
        widget.pack(fill="both", expand=True)
        if isinstance(getattr(self, "_canvas_charts", None), list):
            self._canvas_charts.append(canvas)
        else:
            self._canvas_charts.setdefault(group, []).append(canvas)
        plt.close(fig)

    def _dibujar_mensaje_chart(self, frame, mensaje):
        import tkinter as tk

        tk.Label(
            frame,
            text=mensaje,
            bg=frame["bg"],
            fg=self.C.get("muted", "#64748B"),
            font=("Segoe UI", 9),
            justify="center",
            wraplength=360,
        ).pack(expand=True)

    def _metric_color(self, role):
        mapping = {
            "primary": self.C.get("primary", "#2563EB"),
            "secondary": self.C.get("secondary", "#0F766E"),
            "danger": self.C.get("danger", "#DC2626"),
            "warning": self.C.get("warning", "#D97706"),
        }
        return mapping.get(role, self.C.get("primary", "#2563EB"))

    def _palette(self, total):
        base = [
            self.C.get("primary", "#2563EB"),
            "#0F766E",
            "#0891B2",
            "#D97706",
            self.C.get("danger", "#DC2626"),
            "#14B8A6",
            "#475569",
            "#94A3B8",
            "#38BDF8",
            "#F59E0B",
        ]
        return [base[idx % len(base)] for idx in range(total)]

    def _axis_formatter(self, fmt):
        if fmt == "currency":
            return lambda value, _pos: f"${value:,.0f}"
        if fmt == "percent":
            return lambda value, _pos: f"{value:.0f}%"
        return lambda value, _pos: f"{value:,.0f}"

    def _crear_figura_base(self, width=5.6, height=3.5):
        fig, ax = plt.subplots(figsize=(width, height), facecolor="#FFFFFF")
        ax.set_facecolor("#FFFFFF")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(self.C.get("border", "#E2E8F0"))
        ax.spines["bottom"].set_color(self.C.get("border", "#E2E8F0"))
        ax.tick_params(colors=self.C["text"], labelsize=8)
        ax.grid(axis="y", color=self.C.get("border", "#E2E8F0"), alpha=0.35, linewidth=0.8)
        fig.tight_layout(pad=1.5)
        return fig, ax

    def _figure_size_for_frame(self, frame, default=(6.3, 4.0), min_size=(5.8, 3.8), max_size=(12.0, 7.2)):
        try:
            frame.update_idletasks()
        except Exception:
            return default
        width_px = max(int(frame.winfo_width() or 0), 0)
        height_px = max(int(frame.winfo_height() or 0), 0)
        if width_px <= 1 or height_px <= 1:
            return default
        dpi = float(plt.rcParams.get("figure.dpi", 100) or 100)
        width = max(min_size[0], min(max_size[0], width_px / dpi))
        height = max(min_size[1], min(max_size[1], height_px / dpi))
        return width, height

    def _compactar_para_pie(self, rows, label_key, metric_key):
        rows = sorted(rows, key=lambda item: as_float(item.get(metric_key)), reverse=True)
        if len(rows) <= 6:
            return rows
        visibles = rows[:5]
        otros_valor = sum(as_float(item.get(metric_key)) for item in rows[5:])
        if otros_valor > 0:
            visibles.append({label_key: "Otros", metric_key: otros_valor})
        return visibles

    def _render_rank_chart(self, frame, rows, label_key, metric_label, metric_cfg, chart_type, limit):
        metric_key = metric_cfg["field"]
        metric_fmt = metric_cfg["format"]
        rows = [row for row in rows if as_float(row.get(metric_key)) > 0]
        rows = sorted(rows, key=lambda item: as_float(item.get(metric_key)), reverse=True)[:limit]
        if not rows:
            return self._dibujar_mensaje_chart(frame, "No hay datos suficientes para esta visualizacion.")

        plot_rows = rows
        if chart_type in {"Pastel", "Dona"}:
            plot_rows = self._compactar_para_pie(rows, label_key, metric_key)

        labels = [safe_label(item.get(label_key) or "Sin dato", 26) for item in plot_rows]
        values = [as_float(item.get(metric_key)) for item in plot_rows]
        colors = self._palette(len(plot_rows))

        fig, ax = self._crear_figura_base()
        ax.yaxis.set_major_formatter(FuncFormatter(self._axis_formatter(metric_fmt)))
        ax.xaxis.set_major_formatter(FuncFormatter(self._axis_formatter(metric_fmt)))

        if chart_type == "Barras horizontales":
            ax.grid(axis="x", color=self.C.get("border", "#E2E8F0"), alpha=0.35)
            ax.grid(axis="y", visible=False)
            ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.58)
            ax.xaxis.set_major_formatter(FuncFormatter(self._axis_formatter(metric_fmt)))
        elif chart_type == "Barras verticales":
            x = range(len(labels))
            ax.bar(x, values, color=colors, width=0.62)
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=22, ha="right")
            ax.yaxis.set_major_formatter(FuncFormatter(self._axis_formatter(metric_fmt)))
        elif chart_type == "Linea":
            x = range(len(labels))
            base_color = self.C.get("primary", "#2563EB")
            ax.plot(x, values, color=base_color, linewidth=2.4, marker="o", markersize=5)
            ax.fill_between(x, values, color=base_color, alpha=0.08)
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=20, ha="right")
            ax.yaxis.set_major_formatter(FuncFormatter(self._axis_formatter(metric_fmt)))
        else:
            ax.grid(False)
            wedges, _texts, _autotexts = ax.pie(
                values,
                autopct=lambda pct: f"{pct:.1f}%" if pct >= 5 else "",
                startangle=90,
                colors=colors,
                wedgeprops={"width": 0.42 if chart_type == "Dona" else 1.0, "edgecolor": "#FFFFFF"},
                textprops={"color": self.C["text"], "fontsize": 8},
            )
            ax.legend(
                wedges,
                labels,
                loc="center left",
                bbox_to_anchor=(1.0, 0.5),
                frameon=False,
                fontsize=8,
            )
            ax.set(aspect="equal")

        ax.set_title(metric_label, fontsize=10, fontweight="bold", color=self.C["text"], loc="left")
        fig.tight_layout(pad=1.6)
        self._dibujar_figura(frame, fig, group="dashboard")

    def _render_trend_chart(self, frame, rows, metric_label, metric_cfg, chart_type, limit):
        rows = list(rows or [])[-limit:]
        if not rows:
            return self._dibujar_mensaje_chart(frame, "No hay movimientos en el periodo filtrado para dibujar la tendencia.")

        metric_key = metric_cfg["field"]
        values = [as_float(item.get(metric_key)) for item in rows]
        labels = [
            item.get("fecha").strftime("%d/%m") if hasattr(item.get("fecha"), "strftime") else str(item.get("fecha") or "")
            for item in rows
        ]
        color = self._metric_color(metric_cfg.get("color_role"))

        fig, ax = self._crear_figura_base()
        x = list(range(len(labels)))
        if chart_type == "Linea":
            ax.plot(x, values, color=color, linewidth=2.5, marker="o", markersize=5)
            ax.fill_between(x, values, color=color, alpha=0.10)
        else:
            colors = [
                self.C.get("danger", "#DC2626") if metric_key == "balance" and value < 0 else color
                for value in values
            ]
            ax.bar(x, values, color=colors, width=0.62)

        if metric_key == "balance":
            ax.axhline(0, color=self.C.get("border", "#E2E8F0"), linewidth=1)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=24, ha="right")
        ax.yaxis.set_major_formatter(FuncFormatter(self._axis_formatter(metric_cfg["format"])))
        ax.set_title(metric_label, fontsize=10, fontweight="bold", color=self.C["text"], loc="left")
        fig.tight_layout(pad=1.6)
        self._dibujar_figura(frame, fig, group="dashboard")

    def _get_dashboard_dataset(self, key):
        dashboard = getattr(self, "dashboard_actual", {}) or {}
        datasets = dashboard.get("datasets") or {}
        if key in datasets:
            return list(datasets.get(key) or [])

        legacy_map = {
            "categorias": dashboard.get("categorias", []),
            "movimientos_fecha": dashboard.get("movimientos_fecha", []),
            "productos": dashboard.get("top_productos", []),
            "proveedores": dashboard.get("proveedores", []),
        }
        return list(legacy_map.get(key) or [])

    def _actualizar_dashboard(self, dashboard):
        self.dashboard_actual = dashboard or {}
        self._redibujar_dashboard()

    def _redibujar_dashboard(self):
        self._limpiar_canvases("dashboard")
        if not self._perm("ver_graficos") or not hasattr(self, "chart_panels"):
            return

        for panel in self.chart_panels.values():
            self._limpiar_panel_chart(panel["plot"])

        for key, blueprint in self.chart_blueprints.items():
            panel = self.chart_panels[key]
            state = self.chart_state[key]
            metric_label = state["metric"].get()
            chart_type = state["type"].get()
            limit = label_limit(state["limit"].get())
            metric_cfg = blueprint["metric_options"][metric_label]
            dataset = self._get_dashboard_dataset(blueprint["dataset"])

            if key == "tendencia":
                panel["hint"].config(text=f"{state['limit'].get()} con metrica {metric_label.lower()}.")
                self._render_trend_chart(panel["plot"], dataset, metric_label, metric_cfg, chart_type, limit)
            else:
                panel["hint"].config(text=f"{state['limit'].get()} por {metric_label.lower()}.")
                self._render_rank_chart(
                    panel["plot"],
                    dataset,
                    blueprint["label_key"],
                    metric_label,
                    metric_cfg,
                    chart_type,
                    limit,
                )

    def _render_dynamic_chart(self, frame, chart_payload, group="dynamic_chart"):
        rows = list((chart_payload or {}).get("series") or [])
        chart_type = (chart_payload or {}).get("chart_type") or "Barras verticales"
        y_format = (chart_payload or {}).get("y_format") or "number"
        if not rows:
            return self._dibujar_mensaje_chart(frame, "No hay puntos disponibles para el grafico seleccionado.")

        labels = [safe_label(item.get("x_label") or "Sin dato", 28) for item in rows]
        values = [as_float(item.get("value")) for item in rows]
        colors = self._palette(len(rows))

        fig_width, fig_height = self._figure_size_for_frame(frame, default=(7.2, 4.6), min_size=(6.4, 4.2), max_size=(12.0, 7.2))
        fig, ax = self._crear_figura_base(width=fig_width, height=fig_height)
        ax.yaxis.set_major_formatter(FuncFormatter(self._axis_formatter(y_format)))
        ax.xaxis.set_major_formatter(FuncFormatter(self._axis_formatter(y_format)))

        if chart_type == "Barras horizontales":
            ax.grid(axis="x", color=self.C.get("border", "#E2E8F0"), alpha=0.35)
            ax.grid(axis="y", visible=False)
            ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.58)
        elif chart_type == "Barras verticales":
            x = range(len(labels))
            ax.bar(x, values, color=colors, width=0.62)
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=22, ha="right")
        elif chart_type == "Linea":
            x = range(len(labels))
            color = self.C.get("primary", "#2563EB")
            ax.plot(x, values, color=color, linewidth=2.4, marker="o", markersize=5)
            ax.fill_between(x, values, color=color, alpha=0.08)
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=20, ha="right")
        elif chart_type == "Area":
            x = range(len(labels))
            color = self.C.get("secondary", "#0F766E")
            ax.plot(x, values, color=color, linewidth=2.0)
            ax.fill_between(x, values, color=color, alpha=0.22)
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=20, ha="right")
        else:
            ax.grid(False)
            wedges, _texts, _autotexts = ax.pie(
                values,
                autopct=lambda pct: f"{pct:.1f}%" if pct >= 5 else "",
                startangle=90,
                colors=colors,
                wedgeprops={"width": 0.42 if chart_type == "Dona" else 1.0, "edgecolor": "#FFFFFF"},
                textprops={"color": self.C["text"], "fontsize": 8},
            )
            ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=8)
            ax.set(aspect="equal")

        ax.set_title((chart_payload or {}).get("y_label") or "Grafico", fontsize=10, fontweight="bold", color=self.C["text"], loc="left")
        fig.tight_layout(pad=1.6)
        self._dibujar_figura(frame, fig, group=group)
