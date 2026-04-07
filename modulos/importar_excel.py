import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import re
import unicodedata
from datetime import date, datetime

from modulos.campos_opcionales import obtener_campos_activos
from gui.ui_helpers import bloquear_columnas, configurar_ventana


class ImportarExcelWindow:
    """
    Importación masiva de productos desde Excel.

    Validaciones ANTES de importar:
      1. Columnas mínimas requeridas (nombre o codigo + precio_unitario)
      2. Duplicados DENTRO del Excel: mismo codigo O mismo nombre en más de una fila
      3. Filas con datos inválidos (precio negativo, cantidad no numérica, etc.)

    En la BD la detección de existente usa:
      - Primero busca por 'codigo' (si se proporcionó)
      - Si no, busca por 'nombre'
    """

    COLUMNAS_BASE = ['codigo', 'nombre', 'descripcion', 'cantidad',
                     'precio_compra', 'precio_unitario', 'stock_minimo', 'stock_maximo',
                     'unidad_medida', 'proveedor', 'categoria']

    ALIASES_COLUMNAS_BASE = {
        'codigo': {'codigo', 'cod', 'sku', 'codigo_sku', 'codigo_producto'},
        'nombre': {'nombre', 'producto', 'nombre_producto'},
        'descripcion': {'descripcion', 'detalle', 'detalle_producto'},
        'cantidad': {'cantidad', 'stock', 'existencia', 'existencias'},
        'precio_compra': {'precio_compra', 'precio_costo', 'costo', 'costo_unitario'},
        'precio_unitario': {'precio_unitario', 'precio', 'precio_venta', 'venta_unitaria', 'pvp'},
        'stock_minimo': {'stock_minimo', 'stock_min', 'minimo', 'stock_bajo'},
        'stock_maximo': {'stock_maximo', 'stock_max', 'maximo', 'tope_stock'},
        'unidad_medida': {'unidad_medida', 'unidad', 'medida', 'unidad_inventario'},
        'proveedor': {'proveedor', 'suplidor', 'supplier'},
        'categoria': {'categoria', 'rubro', 'tipo', 'familia'},
    }

    def __init__(self, master, db, C, usuario):
        self.db      = db
        self.C       = C
        self.usuario = usuario
        self._datos  = []          # filas limpias listas para importar
        self._problemas = []       # lista de (fila, tipo, detalle) con problemas detectados
        self._campos_opcionales = obtener_campos_activos(db)
        self.COLUMNAS = self.COLUMNAS_BASE + [c['key'] for c in self._campos_opcionales]
        self._aliases_columnas = self._construir_aliases_columnas()

        self.win = tk.Toplevel(master)
        self.win.title("📥 Importar Productos desde Excel")
        self.win.configure(bg=C['bg'])
        self.win.grab_set()
        configurar_ventana(self.win, size='main', min_width=1200, min_height=760, start_maximized=True)
        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _texto_columnas_reconocidas(self):
        columnas = list(self.COLUMNAS_BASE)
        columnas.extend(c['key'] for c in self._campos_opcionales)
        etiquetas = []
        for col in columnas:
            if col == 'codigo':
                etiquetas.append('codigo (opcional)')
            elif col in ('nombre', 'precio_unitario'):
                etiquetas.append(f'{col}*')
            else:
                etiquetas.append(col)
        return ', '.join(etiquetas)

    @staticmethod
    def _normalizar_valor_excel(valor):
        if isinstance(valor, datetime):
            return valor.strftime('%Y-%m-%d')
        if isinstance(valor, date):
            return valor.strftime('%Y-%m-%d')
        return valor

    @staticmethod
    def _normalizar_cabecera(valor):
        texto = unicodedata.normalize('NFKD', str(valor or ''))
        texto = texto.encode('ascii', 'ignore').decode('ascii').lower().strip()
        texto = re.sub(r'[^a-z0-9]+', '_', texto).strip('_')
        return texto

    def _construir_aliases_columnas(self):
        aliases = {
            clave: {self._normalizar_cabecera(alias) for alias in valores}
            for clave, valores in self.ALIASES_COLUMNAS_BASE.items()
        }
        for campo in self._campos_opcionales:
            aliases.setdefault(campo['key'], set()).update({
                self._normalizar_cabecera(campo['key']),
                self._normalizar_cabecera(campo['label']),
                self._normalizar_cabecera(campo.get('col_tabla', '')),
            })
        return aliases

    def _mapear_cabecera(self, valor):
        cabecera = self._normalizar_cabecera(valor)
        if not cabecera:
            return None
        for columna, aliases in self._aliases_columnas.items():
            if cabecera in aliases:
                return columna
        return cabecera if cabecera in self.COLUMNAS else None

    def _ejemplos_plantilla(self):
        ejemplos = [
            {
                'codigo': 'PROD-001', 'nombre': 'Monitor LG 24"',
                'descripcion': 'Full HD IPS 75Hz', 'cantidad': 10,
                'precio_unitario': 250.00, 'stock_minimo': 5, 'stock_maximo': 40,
                'unidad_medida': 'Unidad', 'proveedor': 'LG Electronics',
                'categoria': 'Electrónica',
            },
            {
                'codigo': 'PROD-002', 'nombre': 'Teclado Mecánico',
                'descripcion': 'Switch Blue, retroiluminado', 'cantidad': 15,
                'precio_unitario': 85.00, 'stock_minimo': 3, 'stock_maximo': 30,
                'unidad_medida': 'Unidad', 'proveedor': 'Logitech',
                'categoria': 'Periféricos',
            },
        ]

        for campo in self._campos_opcionales:
            key = campo['key']
            valores = {
                'codigo_barras': ('7501234567890', '7501234567891'),
                'marca': ('LG', 'Logitech'),
                'modelo': ('24MP400', 'K552'),
                'color': ('Negro', 'Negro'),
                'peso': (3.2, 0.9),
                'ubicacion': ('A-01', 'B-03'),
                'numero_serie': ('SN-MON-001', 'SN-TEC-002'),
                'garantia_meses': (12, 6),
                'fecha_vence': ('', ''),
                'impuesto_pct': (15, 15),
            }.get(key, ('', ''))
            ejemplos[0][key], ejemplos[1][key] = valores

        return ejemplos

    def _build(self):
        C = self.C

        ttk.Label(self.win, text="📥 Importar Productos desde Excel",
                  style='Header.TLabel').pack(pady=(14, 2), padx=16, anchor='w')
        ttk.Label(self.win,
                  text=f"Columnas reconocidas: {self._texto_columnas_reconocidas()}",
                  foreground='#64748B', wraplength=900).pack(padx=16, anchor='w')

        # Botones superiores
        frm_top = ttk.Frame(self.win)
        frm_top.pack(fill=tk.X, padx=16, pady=10)

        ttk.Button(frm_top, text="📄 Descargar Plantilla",
                   command=self._descargar_plantilla,
                   style='Neutral.TButton').pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(frm_top, text="📂 Cargar Archivo Excel",
                   command=self._cargar_archivo).pack(side=tk.LEFT)

        self.lbl_archivo = ttk.Label(frm_top, text="Ningún archivo cargado",
                                      foreground='#64748B')
        self.lbl_archivo.pack(side=tk.LEFT, padx=14)

        # Notebook: Previsualización | Problemas detectados
        self.nb = ttk.Notebook(self.win)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))

        self.tab_prev = ttk.Frame(self.nb)
        self.nb.add(self.tab_prev, text="👁️ Previsualización")

        self.tab_prob = ttk.Frame(self.nb)
        self.nb.add(self.tab_prob, text="⚠️ Problemas detectados (0)")

        self._build_tab_prev()
        self._build_tab_prob()

        # Barra inferior
        frm_bot = ttk.Frame(self.win)
        frm_bot.pack(fill=tk.X, padx=16, pady=(0, 12))

        self.lbl_conteo = ttk.Label(frm_bot, text="", foreground='#64748B')
        self.lbl_conteo.pack(side=tk.LEFT)

        self.btn_importar = ttk.Button(frm_bot,
                                        text="✅ Confirmar Importación",
                                        command=self._importar,
                                        style='Create.TButton',
                                        state='disabled')
        self.btn_importar.pack(side=tk.RIGHT)

    def _build_tab_prev(self):
        frm = ttk.Frame(self.tab_prev)
        frm.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        sb_y = ttk.Scrollbar(frm); sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x = ttk.Scrollbar(frm, orient=tk.HORIZONTAL)
        sb_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree = ttk.Treeview(
            frm, columns=self.COLUMNAS, show='headings',
            yscrollcommand=sb_y.set, xscrollcommand=sb_x.set, height=12)
        sb_y.config(command=self.tree.yview)
        sb_x.config(command=self.tree.xview)

        anchos = {'codigo': 100, 'nombre': 180, 'descripcion': 180,
                  'cantidad': 70, 'precio_compra': 95, 'precio_unitario': 95,
                  'stock_minimo': 85, 'stock_maximo': 85,
                  'unidad_medida': 100, 'proveedor': 140, 'categoria': 100}
        for c in self.COLUMNAS:
            self.tree.heading(c, text=c.replace('_', ' ').title())
            self.tree.column(c, width=anchos.get(c, 100),
                             minwidth=anchos.get(c, 80))

        self.tree.tag_configure('dup_excel', background='#FEF9C3', foreground='#854D0E')
        self.tree.tag_configure('ok',        background='#F0FDF4')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(self.tree)

    def _build_tab_prob(self):
        frm = ttk.Frame(self.tab_prob)
        frm.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        sb = ttk.Scrollbar(frm); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('Fila Excel', 'Tipo', 'Detalle')
        self.tree_prob = ttk.Treeview(frm, columns=cols, show='headings',
                                       yscrollcommand=sb.set, height=14)
        sb.config(command=self.tree_prob.yview)
        for c, w in zip(cols, [90, 180, 480]):
            self.tree_prob.heading(c, text=c)
            self.tree_prob.column(c, width=w)
        self.tree_prob.tag_configure('error', background='#FEF2F2', foreground='#991B1B')
        self.tree_prob.tag_configure('warn',  background='#FEF9C3', foreground='#854D0E')
        self.tree_prob.pack(fill=tk.BOTH, expand=True)
        self.tree_prob.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(self.tree_prob)

  