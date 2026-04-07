import tkinter as tk
import warnings
warnings.filterwarnings("ignore", "Tight layout")
from tkinter import ttk, filedialog, messagebox
import os
from gui.ui_helpers import bloquear_columnas, configurar_ventana

import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt

COLORES = ['#2563EB','#10B981','#EF4444','#F59E0B','#7C3AED','#0EA5E9','#F97316','#14B8A6']


class ExcelAnalyzer:
    """
    Analizador de Excel — 3 pestañas:
      1. Datos        — tabla con búsqueda, filtros, ordenamiento, exportar filtrado
      2. Estadísticas — resumen por columna
      3. Gráficas     — Automáticas (con Top N, agrupación, función) + Constructor manual
                        Todos los gráficos usan df_view (datos filtrados actualmente visibles)
    """

    def __init__(self, master):
        self.master     = master
        self.df         = None
        self.df_view    = None
        self.fig        = None
        self._win       = None
        self._orden_col = None
        self._orden_asc = True

    def open_window(self):
        if self._win and self._win.winfo_exists():
            self._win.lift(); self._win.focus_force(); return
        self._build()

    # ══════════════════════════════════════════════════════════════════════════
    # VENTANA PRINCIPAL
    # ══════════════════════════════════════════════════════════════════════════

    def _build(self):
        self._win = tk.Toplevel(self.master)
        self._win.title("🔍 Analizador de Excel")
        self._win.configure(bg='#F1F5F9')
        configurar_ventana(self._win, size='xl', min_width=1180, min_height=760)
        self._win.lift(); self._win.focus_force()

        top = tk.Frame(self._win, bg='#1E3A5F', height=50)
        top.pack(fill=tk.X); top.pack_propagate(False)
        tk.Label(top, text="🔍  Analizador de Excel",
                 font=("Segoe UI", 12, "bold"), bg='#1E3A5F', fg='white'
                 ).pack(side=tk.LEFT, padx=16)
        ttk.Button(top, text="💾 Exportar gráfico",
                   command=self._exportar_grafico,
                   style='Neutral.TButton').pack(side=tk.RIGHT, padx=8, pady=8)
        ttk.Button(top, text="📂 Cargar Excel",
                   command=self._cargar).pack(side=tk.RIGHT, padx=4, pady=8)
        self.lbl_archivo = tk.Label(top, text="Ningún archivo cargado",
                                     font=("Segoe UI", 9), bg='#1E3A5F', fg='#94A3B8')
        self.lbl_archivo.pack(side=tk.LEFT, padx=12)

        self.nb = ttk.Notebook(self._win)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 12))

        self.tab_datos = ttk.Frame(self.nb); self.nb.add(self.tab_datos, text="📋  Datos")
        self.tab_stats = ttk.Frame(self.nb); self.nb.add(self.tab_stats, text="📊  Estadísticas")
        self.tab_graf  = ttk.Frame(self.nb); self.nb.add(self.tab_graf,  text="📈  Gráficas")

        self._build_tab_datos()
        self._build_tab_stats()
        self._build_tab_graficas()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — DATOS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_datos(self):
        frm_f = ttk.LabelFrame(self.tab_datos, text="🔎 Búsqueda y filtros", padding=8)
        frm_f.pack(fill=tk.X, padx=10, pady=(10, 4))
        row = ttk.Frame(frm_f); row.pack(fill=tk.X)

        ttk.Label(row, text="Buscar en todo:").pack(side=tk.LEFT, padx=(0, 4))
        self.e_buscar = ttk.Entry(row, width=22)
        self.e_buscar.pack(side=tk.LEFT, padx=(0, 14))
        self.e_buscar.bind('<KeyRelease>', lambda e: self._aplicar_filtros())

        ttk.Label(row, text="Columna:").pack(side=tk.LEFT, padx=(0, 4))
        self.cb_filtro_col = ttk.Combobox(row, state='readonly', width=16)
        self.cb_filtro_col.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Label(row, text="Condición:").pack(side=tk.LEFT, padx=(0, 4))
        self.cb_cond = ttk.Combobox(row, state='readonly', width=14,
                                     values=['contiene','igual a','mayor que',
                                             'menor que','no vacío','vacío'])
        self.cb_cond.set('contiene'); self.cb_cond.pack(side=tk.LEFT, padx=(0, 6))

        self.e_filtro_val = ttk.Entry(row, width=14)
        self.e_filtro_val.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(row, text="✔ Filtrar",
                   command=self._aplicar_filtros).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="✖ Limpiar",
                   command=self._limpiar_filtros,
                   style='Neutral.TButton').pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="📥 Exportar filtrado",
                   command=self._exportar_filtrado,
                   style='Neutral.TButton').pack(side=tk.RIGHT, padx=4)

        frm_t = ttk.Frame(self.tab_datos)
        frm_t.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 2))
        sb_y = ttk.Scrollbar(frm_t); sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x = ttk.Scrollbar(frm_t, orient=tk.HORIZONTAL); sb_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree_datos = ttk.Treeview(frm_t, yscrollcommand=sb_y.set,
                                        xscrollcommand=sb_x.set, height=22)
        sb_y.config(command=self.tree_datos.yview)
        sb_x.config(command=self.tree_datos.xview)
        self.tree_datos.pack(fill=tk.BOTH, expand=True)
        self.tree_datos.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(self.tree_datos)
        self.lbl_conteo = ttk.Label(self.tab_datos, text="", foreground='#64748B')
        self.lbl_conteo.pack(pady=(0, 4))

    def _poblar_preview(self):
        df = self.df_view
        if df is None: return
        self.tree_datos.delete(*self.tree_datos.get_children())
        cols = list(df.columns)
        self.tree_datos['columns'] = cols
        self.tree_datos['show']    = 'headings'
        for col in cols:
            self.tree_datos.heading(col, text=str(col),
                                     command=lambda c=col: self._ordenar_col(c))
            self.tree_datos.column(col, width=130, anchor='w')
        for _, row in df.head(500).iterrows():
            self.tree_datos.insert('', tk.END, values=list(row))
        total = len(self.df) if self.df is not None else 0
        shown = len(df)
        self.lbl_conteo.config(
            text=f"  Mostrando {min(shown,500)} de {shown} filtradas  "
                 f"(total: {total})  |  {len(cols)} columnas")

    def _ordenar_col(self, col):
        if self.df_view is None: return
        asc = not self._orden_asc if self._orden_col == col else True
        try:
            self.df_view = self.df_view.sort_values(
                col, ascending=asc, key=lambda x: pd.to_numeric(x, errors='ignore'))
        except Exception:
            self.df_view = self.df_view.sort_values(col, ascending=asc)
        self._orden_col = col; self._orden_asc = asc
        self._poblar_preview()

    def _aplicar_filtros(self):
        if self.df is None: return
        res = self.df.copy()
        txt = self.e_buscar.get().strip().lower()
        if txt:
            mask = res.apply(lambda r: r.astype(str).str.lower().str.contains(txt).any(), axis=1)
            res  = res[mask]
        col  = self.cb_filtro_col.get()
        cond = self.cb_cond.get()
        val  = self.e_filtro_val.get().strip()
        if col and col in res.columns and cond:
            try:
                if   cond == 'contiene'  and val:
                    res = res[res[col].astype(str).str.lower().str.contains(val.lower(), na=False)]
                elif cond == 'igual a'   and val:
                    try:    res = res[pd.to_numeric(res[col]) == float(val)]
                    except: res = res[res[col].astype(str) == val]
                elif cond == 'mayor que' and val:
                    res = res[pd.to_numeric(res[col], errors='coerce') > float(val)]
                elif cond == 'menor que' and val:
                    res = res[pd.to_numeric(res[col], errors='coerce') < float(val)]
                elif cond == 'no vacío':
                    res = res[res[col].notna() & (res[col].astype(str).str.strip() != '')]
                elif cond == 'vacío':
                    res = res[res[col].isna()  | (res[col].astype(str).str.strip() == '')]
            except Exception: pass
        self.df_view = res
        self._poblar_preview()
        self._actualizar_badge_filtro()

    def _limpiar_filtros(self):
        self.e_buscar.delete(0, tk.END)
        self.e_filtro_val.delete(0, tk.END)
        self.cb_cond.set('contiene')
        if self.df is not None:
            self.df_view = self.df.copy()
            self._poblar_preview()
            self._actualizar_badge_filtro()

    def _actualizar_badge_filtro(self):
        """Actualiza el badge en la pestaña Gráficas indicando cuántas filas hay."""
        if self.df is None or self.df_view is None: return
        total    = len(self.df)
        filtrado = len(self.df_view)
        if filtrado < total:
            txt = f"  ⚠️  Gráficas usarán {filtrado} filas filtradas (de {total} totales)"
            self.lbl_fuente_graf.config(text=txt, foreground='#D97706')
        else:
            self.lbl_fuente_graf.config(
                text=f"  📊  Gráficas usarán todos los datos ({total} filas)",
                foreground='#065F46')

    def _exportar_filtrado(self):
        if self.df_view is None or self.df_view.empty:
            messagebox.showwarning("⚠️", "No hay datos para exportar.", parent=self._win); return
        ruta = filedialog.asksaveasfilename(
            parent=self._win, defaultextension='.xlsx',
            filetypes=[("Excel","*.xlsx")], initialfile="datos_filtrados.xlsx")
        if not ruta: return
        try:
            self.df_view.to_excel(ruta, index=False)
            messagebox.showinfo("✅", f"Guardado en:\n{ruta}", parent=self._win)
        except Exception as e:
            messagebox.showerror("❌ Error", str(e), parent=self._win)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — ESTADÍSTICAS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_stats(self):
        self.frm_stats = ttk.Frame(self.tab_stats)
        self.frm_stats.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        ttk.Label(self.frm_stats, text="Cargue un archivo para ver las estadísticas.",
                  foreground='#64748B').pack(pady=40)

    def _poblar_stats(self):
        for w in self.frm_stats.winfo_children(): w.destroy()
        if self.df is None: return
        num_cols  = self.df.select_dtypes(include='number').columns.tolist()
        text_cols = self.df.select_dtypes(exclude='number').columns.tolist()
        headers   = ['Columna','Tipo','Total','Vacíos','Únicos','Mín','Máx','Promedio','Suma total']
        frm_t = ttk.Frame(self.frm_stats); frm_t.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(frm_t); sb.pack(side=tk.RIGHT, fill=tk.Y)
        tree = ttk.Treeview(frm_t, columns=headers, show='headings',
                             yscrollcommand=sb.set, height=22)
        sb.config(command=tree.yview)
        for h, w in zip(headers, [160,75,60,60,65,90,90,90,110]):
            tree.heading(h, text=h); tree.column(h, width=w, anchor='center')
        tree.tag_configure('num',  background='#EFF6FF')
        tree.tag_configure('text', background='#F0FDF4')
        for col in num_cols:
            s = self.df[col]; sn = s.dropna()
            tree.insert('', tk.END, tags=('num',), values=(
                col,'Numérico',len(s),int(s.isna().sum()),s.nunique(),
                f"{sn.min():.2f}" if len(sn) else '-',
                f"{sn.max():.2f}" if len(sn) else '-',
                f"{sn.mean():.2f}" if len(sn) else '-',
                f"{sn.sum():.2f}" if len(sn) else '-'))
        for col in text_cols:
            s = self.df[col]
            tree.insert('', tk.END, tags=('text',), values=(
                col,'Texto',len(s),int(s.isna().sum()),s.nunique(),'-','-','-','-'))
        tree.pack(fill=tk.BOTH, expand=True)
        tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(tree)
        dups = int(self.df.duplicated().sum())
        ttk.Label(self.frm_stats,
                  text=f"  📋 {len(self.df)} filas  |  {len(self.df.columns)} columnas  "
                       f"|  🔁 {dups} filas duplicadas",
                  foreground='#475569').pack(pady=(4,0))

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — GRÁFICAS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_graficas(self):
        # Badge que muestra cuántas filas usarán las gráficas
        self.lbl_fuente_graf = tk.Label(self.tab_graf, text="",
                                         font=("Segoe UI", 9),
                                         bg='#F1F5F9', fg='#64748B', anchor='w')
        self.lbl_fuente_graf.pack(fill=tk.X, padx=10, pady=(6, 0))

        nb_g = ttk.Notebook(self.tab_graf)
        nb_g.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        self.tab_auto   = ttk.Frame(nb_g); nb_g.add(self.tab_auto,   text="✨  Automáticas")
        self.tab_manual = ttk.Frame(nb_g); nb_g.add(self.tab_manual, text="🔧  Constructor manual")

        self._build_subtab_auto()
        self._build_subtab_manual()

    # ── Sub-tab Automáticas ───────────────────────────────────────────────────

    def _build_subtab_auto(self):
        # ── Controles de configuración ────────────────────────────────────────
        frm_cfg = ttk.LabelFrame(self.tab_auto, text="⚙️  Configuración de la gráfica", padding=8)
        frm_cfg.pack(fill=tk.X, padx=10, pady=(8, 4))

        row1 = ttk.Frame(frm_cfg); row1.pack(fill=tk.X, pady=(0, 6))

        # Agrupar por
        ttk.Label(row1, text="Agrupar por:").pack(side=tk.LEFT, padx=(0,4))
        self.cb_agrupar = ttk.Combobox(row1, state='readonly', width=18)
        self.cb_agrupar.pack(side=tk.LEFT, padx=(0, 14))

        # Columna de valor
        ttk.Label(row1, text="Valor:").pack(side=tk.LEFT, padx=(0,4))
        self.cb_valor = ttk.Combobox(row1, state='readonly', width=18)
        self.cb_valor.pack(side=tk.LEFT, padx=(0, 14))

        # Función de agregación
        ttk.Label(row1, text="Función:").pack(side=tk.LEFT, padx=(0,4))
        self.cb_funcion = ttk.Combobox(row1, state='readonly', width=10,
                                        values=['Suma','Promedio','Máximo','Mínimo','Conteo'])
        self.cb_funcion.set('Suma'); self.cb_funcion.pack(side=tk.LEFT, padx=(0, 14))

        # Top N
        ttk.Label(row1, text="Top N:").pack(side=tk.LEFT, padx=(0,4))
        self.spin_n = ttk.Spinbox(row1, from_=3, to=50, width=5, value=10)
        self.spin_n.set(10); self.spin_n.pack(side=tk.LEFT, padx=(0, 14))

        # Tipo de gráfica automática
        ttk.Label(row1, text="Tipo:").pack(side=tk.LEFT, padx=(0,4))
        self.cb_tipo_auto = ttk.Combobox(row1, state='readonly', width=18,
                                          values=['Barras horizontales (Top N)',
                                                  'Barras verticales (Top N)',
                                                  'Pastel (Top N)',
                                                  'Histograma (distribución)',
                                                  'Boxplot por grupo',
                                                  'Tendencia (todos los datos)'])
        self.cb_tipo_auto.set('Barras horizontales (Top N)')
        self.cb_tipo_auto.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(row1, text="📈 Generar",
                   command=self._generar_auto).pack(side=tk.LEFT)

        # Sugerencias rápidas (se generan al cargar archivo)
        frm_sug = ttk.Frame(self.tab_auto); frm_sug.pack(fill=tk.X, padx=10, pady=(0, 4))
        self.frm_auto_btn = frm_sug
        ttk.Label(frm_sug, text="Sugerencias rápidas:",
                  foreground='#64748B').pack(side=tk.LEFT, padx=(0,8))

        # Área del gráfico con scroll
        self.frm_auto_graf = ttk.LabelFrame(self.tab_auto, text="Vista previa", padding=4)
        self.frm_auto_graf.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        ttk.Label(self.frm_auto_graf,
                  text="Configure los parámetros y haga clic en 'Generar'.",
                  foreground='#64748B').pack(pady=60)

    def _generar_botones_auto(self):
        """Sugerencias rápidas y rellena los combos de configuración."""
        for w in list(self.frm_auto_btn.winfo_children()):
            if isinstance(w, ttk.Button): w.destroy()
        if self.df is None: return

        num = self.df.select_dtypes(include='number').columns.tolist()
        txt = self.df.select_dtypes(exclude='number').columns.tolist()

        # Llenar combos
        self.cb_agrupar['values'] = ['(ninguno)'] + txt + num
        self.cb_agrupar.set(txt[0] if txt else '(ninguno)')
        self.cb_valor['values']   = num
        self.cb_valor.set(num[0] if num else '')

        # Sugerencias según tamaño del dataset
        n = len(self.df)
        sug = []
        if txt and num:
            sug.append((f"🏆 Top por '{txt[0]}'",
                         lambda t=txt[0], v=num[0]: self._sugerencia('top', t, v)))
            sug.append((f"🥧 Pastel '{txt[0]}'",
                         lambda t=txt[0], v=num[0]: self._sugerencia('pie', t, v)))
        if num:
            sug.append((f"📦 Distribución '{num[0]}'",
                         lambda v=num[0]: self._sugerencia('hist', None, v)))
        if num and n <= 200:
            sug.append((f"📈 Tendencia '{num[0]}'",
                         lambda v=num[0]: self._sugerencia('trend', None, v)))
        if txt and num and n > 50:
            sug.append((f"📊 Boxplot '{txt[0]}'",
                         lambda t=txt[0], v=num[0]: self._sugerencia('box', t, v)))

        for lbl, cmd in sug:
            ttk.Button(self.frm_auto_btn, text=lbl, command=cmd
                       ).pack(side=tk.LEFT, padx=3, pady=3)

    def _sugerencia(self, tipo_sug, col_grp, col_val):
        """Aplica una sugerencia rápida y genera la gráfica."""
        mapa = {
            'top':   'Barras horizontales (Top N)',
            'pie':   'Pastel (Top N)',
            'hist':  'Histograma (distribución)',
            'trend': 'Tendencia (todos los datos)',
            'box':   'Boxplot por grupo',
        }
        self.cb_tipo_auto.set(mapa.get(tipo_sug, 'Barras horizontales (Top N)'))
        if col_grp: self.cb_agrupar.set(col_grp)
        if col_val: self.cb_valor.set(col_val)
        self._generar_auto()

    def _generar_auto(self):
        if self.df_view is None:
            messagebox.showwarning("⚠️", "Primero cargue un archivo.", parent=self._win); return

        df     = self.df_view.copy()
        grp    = self.cb_agrupar.get()
        val    = self.cb_valor.get()
        func   = self.cb_funcion.get()
        tipo   = self.cb_tipo_auto.get()
        try:   n = int(self.spin_n.get())
        except: n = 10

        if not val or val not in df.columns:
            messagebox.showwarning("⚠️", "Seleccione una columna de valor.", parent=self._win); return

        # ── Aviso y recomendación para datasets grandes ───────────────────────
        filas = len(df)
        if filas > 200 and tipo in ('Barras horizontales (Top N)', 'Barras verticales (Top N)', 'Pastel (Top N)'):
            if grp == '(ninguno)' or grp not in df.columns:
                messagebox.showinfo(
                    "💡 Sugerencia para datasets grandes",
                    f"Tienes {filas} filas. Para que la gráfica sea legible:\n\n"
                    f"• Selecciona una columna de 'Agrupar por' (ej. categoría, proveedor)\n"
                    f"• El sistema sumará/promediará los valores por grupo\n"
                    f"• El Top N mostrará solo los grupos más relevantes\n\n"
                    f"Si graficas {filas} filas individuales el resultado será ilegible.",
                    parent=self._win)
                return

        # ── Función de agregación ─────────────────────────────────────────────
        func_map = {'Suma': 'sum','Promedio': 'mean',
                    'Máximo': 'max','Mínimo': 'min','Conteo': 'count'}
        agg = func_map.get(func, 'sum')

        try:
            if tipo == 'Histograma (distribución)':
                self._g_histograma_v2(df, val)
                return
            if tipo == 'Tendencia (todos los datos)':
                self._g_tendencia_v2(df, val)
                return
            if tipo == 'Boxplot por grupo':
                if grp == '(ninguno)' or grp not in df.columns:
                    messagebox.showwarning("⚠️", "Seleccione una columna para agrupar.", parent=self._win); return
                self._g_boxplot(df, grp, val, n)
                return

            # Agrupar
            if grp != '(ninguno)' and grp in df.columns:
                serie = getattr(df.groupby(grp)[val], agg)().nlargest(n)
                titulo_suf = f"por '{grp}' — {func} de '{val}' (Top {n})"
            else:
                serie = pd.to_numeric(df[val], errors='coerce').dropna()
                serie = serie.nlargest(n)
                serie.index = [f"Fila {i}" for i in serie.index]
                titulo_suf = f"'{val}' (Top {n} valores)"

            if tipo == 'Barras horizontales (Top N)':
                self._g_barras_h(serie, titulo_suf, val)
            elif tipo == 'Barras verticales (Top N)':
                self._g_barras_v(serie, titulo_suf, val)
            elif tipo == 'Pastel (Top N)':
                self._g_pastel(serie, titulo_suf)

        except Exception as e:
            messagebox.showerror("❌ Error", str(e), parent=self._win)

    # ── Generadores de gráficas ───────────────────────────────────────────────

    def _mostrar_grafico_auto(self, fig):
        for w in self.frm_auto_graf.winfo_children(): w.destroy()
        self.fig = fig
        fig.patch.set_facecolor('white')
        canvas = FigureCanvasTkAgg(fig, master=self.frm_auto_graf)
        canvas.draw()
        NavigationToolbar2Tk(canvas, self.frm_auto_graf).update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _g_barras_h(self, serie, titulo, xlabel):
        """Barras horizontales con altura dinámica según cantidad de elementos."""
        n    = len(serie)
        alto = max(4, n * 0.40)   # altura dinámica
        fig, ax = plt.subplots(figsize=(10, alto))
        etiq = [str(e)[:25] for e in serie.index]   # truncar labels largos
        bars = ax.barh(etiq[::-1], serie.values[::-1],
                       color=COLORES[0], alpha=0.87)
        # Etiquetas de valor solo si hay espacio
        if n <= 30:
            ax.bar_label(bars, fmt='%.1f', padding=4, fontsize=8)
        ax.set_title(titulo, fontweight='bold', fontsize=11, pad=12)
        ax.set_xlabel(xlabel)
        ax.grid(axis='x', alpha=0.25)
        if n > 10:
            ax.tick_params(axis='y', labelsize=8)
        fig.tight_layout()
        self._mostrar_grafico_auto(fig)

    def _g_barras_v(self, serie, titulo, ylabel):
        n    = len(serie)
        fig, ax = plt.subplots(figsize=(max(8, n * 0.6), 5))
        etiq = [str(e)[:18] for e in serie.index]
        ax.bar(range(n), serie.values, color=COLORES[0], alpha=0.87)
        ax.set_xticks(range(n))
        rot = 45 if n > 6 else 0
        ax.set_xticklabels(etiq, rotation=rot, ha='right' if rot else 'center',
                           fontsize=8 if n > 10 else 9)
        ax.set_ylabel(ylabel)
        ax.set_title(titulo, fontweight='bold', fontsize=11, pad=12)
        ax.grid(axis='y', alpha=0.25)
        fig.tight_layout()
        self._mostrar_grafico_auto(fig)

    def _g_pastel(self, serie, titulo):
        n   = len(serie)
        fig, ax = plt.subplots(figsize=(8, 6))
        pct = '%1.1f%%' if n <= 12 else None   # sin % si hay muchos segmentos
        wedges, texts, autotexts = ax.pie(
            serie.values,
            labels=[str(e)[:20] for e in serie.index],
            autopct=pct, startangle=140,
            colors=COLORES[:n])
        if n > 8:
            for t in texts: t.set_fontsize(7)
        ax.set_title(titulo, fontweight='bold', fontsize=11, pad=12)
        fig.tight_layout()
        self._mostrar_grafico_auto(fig)

    def _g_histograma_v2(self, df, col):
        """Histograma con línea de densidad y estadísticas anotadas."""
        datos = pd.to_numeric(df[col], errors='coerce').dropna()
        n     = len(datos)
        bins  = min(50, max(10, int(n ** 0.5)))   # bins dinámicos
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(datos, bins=bins, color=COLORES[0], alpha=0.82,
                edgecolor='white', linewidth=0.5)
        # Línea de media y mediana
        ax.axvline(datos.mean(),   color='#EF4444', lw=1.5, ls='--',
                   label=f"Media: {datos.mean():.1f}")
        ax.axvline(datos.median(), color='#10B981', lw=1.5, ls='-.',
                   label=f"Mediana: {datos.median():.1f}")
        ax.legend(fontsize=9)
        ax.set_title(f"Distribución de '{col}'  ({n} valores)",
                     fontweight='bold', fontsize=11, pad=12)
        ax.set_xlabel(col); ax.set_ylabel("Frecuencia")
        ax.grid(axis='y', alpha=0.25)
        fig.tight_layout()
        self._mostrar_grafico_auto(fig)

    def _g_tendencia_v2(self, df, col):
        """Tendencia con media móvil cuando hay muchos datos."""
        datos = pd.to_numeric(df[col], errors='coerce').dropna().reset_index(drop=True)
        n     = len(datos)
        fig, ax = plt.subplots(figsize=(10, 4))
        # Con muchos datos solo mostrar puntos si son pocos
        ms = 3 if n < 100 else 0
        ax.plot(datos.index, datos.values, color=COLORES[0],
                lw=1.4, alpha=0.7, marker='o', ms=ms, label=col)
        # Media móvil si hay suficientes datos
        if n >= 10:
            ventana = max(3, n // 20)
            mm = datos.rolling(ventana, center=True).mean()
            ax.plot(mm.index, mm.values, color='#EF4444',
                    lw=2, label=f"Media móvil ({ventana})")
        ax.fill_between(datos.index, datos.values, alpha=0.10, color=COLORES[0])
        ax.legend(fontsize=9)
        ax.set_title(f"Tendencia de '{col}'  ({n} filas)",
                     fontweight='bold', fontsize=11, pad=12)
        ax.set_xlabel("Fila"); ax.set_ylabel(col)
        ax.grid(axis='y', alpha=0.25)
        fig.tight_layout()
        self._mostrar_grafico_auto(fig)

    def _g_boxplot(self, df, col_grp, col_val, max_grupos=20):
        """Boxplot por grupo — ideal para datasets grandes."""
        grupos = df[col_grp].astype(str).unique()
        if len(grupos) > max_grupos:
            # Tomar los grupos con más registros
            top_g  = df[col_grp].astype(str).value_counts().nlargest(max_grupos).index
            df     = df[df[col_grp].astype(str).isin(top_g)]
            grupos = top_g
        datos_box = [pd.to_numeric(df[df[col_grp].astype(str) == g][col_val],
                                   errors='coerce').dropna().values
                     for g in grupos]
        datos_box = [d for d in datos_box if len(d) > 0]
        etiq      = [str(e)[:18] for e in grupos][:len(datos_box)]

        n_g  = len(datos_box)
        alto = max(4, n_g * 0.35)
        fig, ax = plt.subplots(figsize=(10, alto))
        bp = ax.boxplot(datos_box, vert=False, patch_artist=True,
                        medianprops=dict(color='#EF4444', lw=2))
        for patch, color in zip(bp['boxes'],
                                [COLORES[i % len(COLORES)] for i in range(n_g)]):
            patch.set_facecolor(color); patch.set_alpha(0.7)
        ax.set_yticklabels(etiq, fontsize=8 if n_g > 10 else 9)
        ax.set_title(f"Boxplot de '{col_val}' por '{col_grp}'",
                     fontweight='bold', fontsize=11, pad=12)
        ax.set_xlabel(col_val)
        ax.grid(axis='x', alpha=0.25)
        fig.tight_layout()
        self._mostrar_grafico_auto(fig)

    # ── Sub-tab Constructor manual ────────────────────────────────────────────

    def _build_subtab_manual(self):
        paned = ttk.PanedWindow(self.tab_manual, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        izq = ttk.LabelFrame(paned, text="⚙️  Configuración", padding=12)
        paned.add(izq, weight=1)

        ttk.Label(izq, text="Eje X (etiquetas):").pack(anchor='w', pady=(0,2))
        self.cb_x = ttk.Combobox(izq, state='readonly', width=28)
        self.cb_x.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(izq, text="Columnas Y — Ctrl+clic para varias:").pack(anchor='w', pady=(0,2))
        frm_lb = ttk.Frame(izq); frm_lb.pack(fill=tk.X, pady=(0, 8))
        sb_lb  = ttk.Scrollbar(frm_lb); sb_lb.pack(side=tk.RIGHT, fill=tk.Y)
        self.lb_y = tk.Listbox(frm_lb, selectmode=tk.MULTIPLE, exportselection=False,
                                height=8, font=('Segoe UI', 9), yscrollcommand=sb_lb.set)
        sb_lb.config(command=self.lb_y.yview)
        self.lb_y.pack(fill=tk.BOTH, expand=True)

        ttk.Label(izq, text="Tipo de gráfica:").pack(anchor='w', pady=(0,2))
        self.cb_tipo = ttk.Combobox(izq, state='readonly', width=28,
                                     values=['Barras','Barras horizontales',
                                             'Línea','Dispersión','Pastel'])
        self.cb_tipo.set('Barras'); self.cb_tipo.pack(fill=tk.X, pady=(0, 8))

        # Límite de filas para el constructor manual
        frm_lim = ttk.Frame(izq); frm_lim.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(frm_lim, text="Límite de filas:").pack(side=tk.LEFT, padx=(0,6))
        self.spin_lim = ttk.Spinbox(frm_lim, from_=10, to=1000, width=7)
        self.spin_lim.set(100)
        self.spin_lim.pack(side=tk.LEFT)
        ttk.Label(frm_lim, text="(evita gráficas ilegibles)",
                  foreground='#94A3B8', font=('Segoe UI',8)).pack(side=tk.LEFT, padx=6)

        ttk.Button(izq, text="📈 Generar gráfica",
                   command=self._generar_manual).pack(fill=tk.X, pady=(0,4))
        ttk.Button(izq, text="🗑️ Limpiar",
                   command=self._limpiar_manual,
                   style='Neutral.TButton').pack(fill=tk.X)

        self.frm_manual_graf = ttk.LabelFrame(paned, text="Gráfica", padding=6)
        paned.add(self.frm_manual_graf, weight=3)
        ttk.Label(self.frm_manual_graf,
                  text="Cargue un archivo, configure los ejes\ny haga clic en 'Generar gráfica'.",
                  foreground='#64748B', justify='center').pack(pady=80)

    def _poblar_controles_manual(self):
        cols     = list(self.df.columns)
        num_cols = self.df.select_dtypes(include='number').columns.tolist()
        self.cb_x['values'] = [''] + cols
        self.cb_x.set(cols[0] if cols else '')
        self.lb_y.delete(0, tk.END)
        for c in cols: self.lb_y.insert(tk.END, c)
        for i, c in enumerate(cols):
            if c in num_cols: self.lb_y.selection_set(i)

    def _generar_manual(self):
        if self.df_view is None:
            messagebox.showwarning("⚠️", "Primero cargue un archivo.", parent=self._win); return
        y_idx = self.lb_y.curselection()
        if not y_idx:
            messagebox.showwarning("⚠️", "Seleccione al menos una columna Y.", parent=self._win); return

        y_cols = [self.lb_y.get(i) for i in y_idx]
        x_col  = self.cb_x.get()
        tipo   = self.cb_tipo.get()
        try:   lim = int(self.spin_lim.get())
        except: lim = 100

        # Aviso si hay más datos que el límite
        total = len(self.df_view)
        if total > lim:
            self.lbl_fuente_graf.config(
                text=f"  ⚠️  Mostrando solo {lim} de {total} filas. "
                     f"Aumenta el límite o usa Automáticas con agrupación.",
                foreground='#D97706')

        # Usar df_view con límite de filas
        df = self.df_view.head(lim)

        try:
            fig, ax = plt.subplots(figsize=(10, 5))
            for idx, col in enumerate(y_cols):
                y = pd.to_numeric(df[col], errors='coerce')
                c = COLORES[idx % len(COLORES)]
                n = len(y)
                if tipo == 'Barras':
                    ax.bar(range(n), y, label=col, color=c, alpha=0.82)
                elif tipo == 'Barras horizontales':
                    fig.set_figheight(max(4, n * 0.28))
                    ax.barh(range(n), y, label=col, color=c, alpha=0.82)
                elif tipo == 'Línea':
                    ms = 3 if n < 80 else 0
                    ax.plot(range(n), y, label=col, color=c,
                            marker='o', ms=ms, lw=1.8)
                elif tipo == 'Dispersión':
                    ax.scatter(range(n), y, label=col, color=c, alpha=0.6, s=20)
                elif tipo == 'Pastel':
                    xl = df[x_col].astype(str) if x_col and x_col in df.columns else None
                    ax.pie(y.dropna(), labels=xl, autopct='%1.1f%%', startangle=140,
                           colors=COLORES[:len(y.dropna())])
                    break

            if tipo != 'Pastel':
                if x_col and x_col in df.columns:
                    etiq = df[x_col].astype(str).tolist()
                    if tipo == 'Barras horizontales':
                        ax.set_yticks(range(len(etiq)))
                        ax.set_yticklabels(
                            [e[:18] for e in etiq],
                            fontsize=8 if len(etiq) > 15 else 9)
                    else:
                        ax.set_xticks(range(len(etiq)))
                        rot = 45 if len(etiq) > 8 else 0
                        ax.set_xticklabels(
                            [e[:15] for e in etiq],
                            rotation=rot, ha='right' if rot else 'center',
                            fontsize=8 if len(etiq) > 12 else 9)
                    ax.set_xlabel(x_col)
                ax.grid(axis='y' if tipo != 'Barras horizontales' else 'x',
                        alpha=0.2)

            h, l = ax.get_legend_handles_labels()
            if h: ax.legend(fontsize=9)
            ax.set_title(
                f"{tipo}: {', '.join(y_cols)}  ({len(df)} filas)",
                fontweight='bold', fontsize=11, pad=12)
            fig.patch.set_facecolor('white')
            fig.tight_layout()

            for w in self.frm_manual_graf.winfo_children(): w.destroy()
            self.fig = fig
            canvas = FigureCanvasTkAgg(fig, master=self.frm_manual_graf)
            canvas.draw()
            NavigationToolbar2Tk(canvas, self.frm_manual_graf).update()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        except Exception as e:
            messagebox.showerror("❌ Error", str(e), parent=self._win)

    def _limpiar_manual(self):
        for w in self.frm_manual_graf.winfo_children(): w.destroy()
        ttk.Label(self.frm_manual_graf,
                  text="Cargue un archivo, configure los ejes\ny haga clic en 'Generar gráfica'.",
                  foreground='#64748B', justify='center').pack(pady=80)
        self.fig = None; plt.close('all')

    # ══════════════════════════════════════════════════════════════════════════
    # CARGAR ARCHIVO
    # ══════════════════════════════════════════════════════════════════════════

    def _cargar(self):
        path = filedialog.askopenfilename(
            parent=self._win,
            filetypes=[("Excel","*.xlsx *.xls"),("Todos","*.*")])
        if not path: return
        try:
            self.df = pd.read_excel(
                path, engine='openpyxl' if path.endswith('.xlsx') else None)
            if self.df.empty:
                messagebox.showwarning("⚠️","El archivo está vacío.", parent=self._win); return
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo leer:\n{e}", parent=self._win); return

        self.df_view = self.df.copy()
        nombre = os.path.basename(path)
        self.lbl_archivo.config(
            text=f"  ✅  {nombre}  —  {len(self.df)} filas × {len(self.df.columns)} columnas",
            fg='#86EFAC')
        self.cb_filtro_col['values'] = [''] + list(self.df.columns)
        self.cb_filtro_col.set('')
        self._poblar_preview()
        self._poblar_stats()
        self._generar_botones_auto()
        self._poblar_controles_manual()
        self._actualizar_badge_filtro()
        self._win.lift(); self._win.focus_force()

    # ══════════════════════════════════════════════════════════════════════════
    # EXPORTAR GRÁFICO
    # ══════════════════════════════════════════════════════════════════════════

    def _exportar_grafico(self):
        if self.fig is None:
            messagebox.showwarning("⚠️","Primero genera una gráfica.", parent=self._win); return
        ruta = filedialog.asksaveasfilename(
            parent=self._win, defaultextension='.png',
            filetypes=[("PNG alta calidad","*.png"),
                       ("PDF vectorial","*.pdf"),
                       ("JPG","*.jpg")],
            initialfile="grafico.png")
        if not ruta: return
        try:
            # dpi alto para PNG, vectorial para PDF
            dpi = 300 if ruta.endswith('.png') else 150
            self.fig.savefig(ruta, dpi=dpi, bbox_inches='tight',
                             facecolor='white', edgecolor='none')
            messagebox.showinfo("✅", f"Gráfico guardado en:\n{ruta}", parent=self._win)
        except Exception as e:
            messagebox.showerror("❌ Error", str(e), parent=self._win)
