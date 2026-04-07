import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from gui.ui_helpers import bloquear_columnas, configurar_ventana


class Dashboard(tk.Toplevel):
    """
    Pantalla de inicio con resumen ejecutivo:
    tarjetas de KPIs, últimos movimientos y mini gráfico de actividad.
    """

    def __init__(self, master, db, C):
        super().__init__(master)
        self.db = db
        self.C  = C
        self.title("🏠 Dashboard — Resumen del Sistema")
        self.configure(bg=C['bg'])
        configurar_ventana(self, width=1180, height=760, min_width=980, min_height=640, resizable=(True, True))
        self._build()

    def _build(self):
        C = self.C

        # ── Encabezado ────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C['header_bg'], height=50)
        hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr, text="🏠  Dashboard — Resumen Ejecutivo",
                 font=("Segoe UI", 13, "bold"), bg=C['header_bg'], fg='white'
                 ).pack(side=tk.LEFT, padx=16)
        tk.Label(hdr, text=datetime.now().strftime("📅  %d/%m/%Y  %H:%M"),
                 font=("Segoe UI", 9), bg=C['header_bg'], fg='#94A3B8'
                 ).pack(side=tk.RIGHT, padx=16)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        # ── Fila de tarjetas KPI ──────────────────────────────────────────────
        stats = self.db.obtener_estadisticas()
        criticos = self.db.obtener_productos_criticos()

        kpis = [
            ("📦", "Productos Activos",  stats.get('total_productos', 0),    C['primary'],   '#EFF6FF'),
            ("📊", "Stock Total",        stats.get('stock_total', 0),         '#0F766E',      '#F0FDFA'),
            ("💰", "Valor Inventario",   f"${stats.get('valor_total',0):.2f}", '#7C3AED',     '#F5F3FF'),
            ("🚨", "Stock Crítico",      stats.get('bajo_stock', 0),           C['danger'],   '#FEF2F2'),
            ("🏭", "Proveedores",        stats.get('total_proveedores', 0),    '#D97706',     '#FFFBEB'),
        ]

        frm_kpi = ttk.Frame(body)
        frm_kpi.pack(fill=tk.X, pady=(0, 12))
        for i, (icon, titulo, valor, color, bg) in enumerate(kpis):
            card = tk.Frame(frm_kpi, bg=bg, relief='flat',
                            highlightbackground=color, highlightthickness=1)
            card.grid(row=0, column=i, padx=6, sticky='nsew')
            frm_kpi.columnconfigure(i, weight=1)
            tk.Label(card, text=icon, font=("Segoe UI", 22),
                     bg=bg).pack(pady=(12, 2))
            tk.Label(card, text=str(valor), font=("Segoe UI", 16, "bold"),
                     bg=bg, fg=color).pack()
            tk.Label(card, text=titulo, font=("Segoe UI", 8),
                     bg=bg, fg='#64748B').pack(pady=(0, 12))

        # ── Fila inferior: movimientos recientes + mini gráfico ───────────────
        frm_bot = ttk.Frame(body)
        frm_bot.pack(fill=tk.BOTH, expand=True)
        frm_bot.columnconfigure(0, weight=2)
        frm_bot.columnconfigure(1, weight=1)

        # Últimos movimientos
        frm_movs = ttk.LabelFrame(frm_bot, text="🕒 Últimos 15 Movimientos", padding=8)
        frm_movs.grid(row=0, column=0, sticky='nsew', padx=(0, 8))

        sb = ttk.Scrollbar(frm_movs); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('Producto', 'Tipo', 'Cantidad', 'Fecha', 'Usuario')
        tree = ttk.Treeview(frm_movs, columns=cols, show='headings',
                             yscrollcommand=sb.set, height=12)
        sb.config(command=tree.yview)
        anchos = {'Producto': 200, 'Tipo': 70, 'Cantidad': 70, 'Fecha': 140, 'Usuario': 100}
        for c in cols:
            tree.heading(c, text=c); tree.column(c, width=anchos[c])
        tree.tag_configure('entrada', foreground='#065F46')
        tree.tag_configure('salida',  foreground='#991B1B')

        movs_recientes = self.db.buscar_movimientos()[:15]
        for m in movs_recientes:
            tipo = str(m.get('tipo_movimiento', '')).lower()
            tag  = 'entrada' if 'entrada' in tipo else 'salida'
            fecha = m['fecha'].strftime('%d/%m/%Y %H:%M') if m.get('fecha') else ''
            tree.insert('', tk.END, tags=(tag,), values=(
                m.get('nombre_producto', ''),
                m.get('tipo_movimiento', ''),
                m.get('cantidad', 0),
                fecha,
                m.get('usuario_nombre') or 'Sistema'))
        tree.pack(fill=tk.BOTH, expand=True)
        tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(tree)

        # Mini gráfico — actividad últimos 7 días
        frm_chart = ttk.LabelFrame(frm_bot, text="📈 Actividad — Últimos 7 días", padding=8)
        frm_chart.grid(row=0, column=1, sticky='nsew')

        hoy    = datetime.now().date()
        inicio = hoy - timedelta(days=6)
        fechas = [inicio + timedelta(days=i) for i in range(7)]
        entradas = {d: 0 for d in fechas}
        salidas  = {d: 0 for d in fechas}

        todos_movs = self.db.obtener_movimientos()
        for m in todos_movs:
            fd = m['fecha'].date() if m.get('fecha') else None
            if fd and fd in entradas:
                t = (m.get('tipo_movimiento') or '').lower()
                if 'entrada' in t:
                    entradas[fd] += int(m.get('cantidad') or 0)
                else:
                    salidas[fd]  += int(m.get('cantidad') or 0)

        etiquetas = [d.strftime('%d/%m') for d in fechas]
        vals_e = [entradas[d] for d in fechas]
        vals_s = [salidas[d]  for d in fechas]

        fig, ax = plt.subplots(figsize=(4.2, 3.8), facecolor=self.C['bg'])
        ax.set_facecolor('#F8FAFC')
        x = range(len(fechas))
        ax.bar([i - 0.2 for i in x], vals_e, width=0.4,
               label='Entradas', color='#10B981', alpha=0.85)
        ax.bar([i + 0.2 for i in x], vals_s, width=0.4,
               label='Salidas',  color='#EF4444', alpha=0.85)
        ax.set_xticks(list(x)); ax.set_xticklabels(etiquetas, fontsize=7)
        ax.tick_params(colors=C['text'], labelsize=7)
        ax.legend(fontsize=7)
        ax.set_title('Entradas vs Salidas', fontsize=9,
                     fontweight='bold', color=C['text'])
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=frm_chart)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Botón actualizar
        ttk.Button(self, text="🔄 Actualizar",
                   command=lambda: [self.destroy(),
                                    Dashboard(self.master, self.db, self.C)]
                   ).pack(pady=(0, 10))
