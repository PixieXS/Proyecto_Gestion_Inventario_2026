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

 