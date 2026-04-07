"""
ingreso_masivo.py — Ventana para ingresar varios productos a la vez.

Flujo:
  1. Se abre una tabla editable con filas vacías.
  2. El usuario llena los campos directamente en la tabla.
  3. [+] agrega nueva fila.  [🗑] borra la fila seleccionada.
  4. "Guardar todos" valida y guarda los productos válidos,
     mostrando un resumen de éxitos y errores.

Validaciones:
  - Nombre y Precio son obligatorios.
  - Cantidad y Precio deben ser numéricos y >= 0.
  - Duplicados internos en la misma tabla (mismo nombre o código).
  - Duplicados con productos ya existentes en la BD.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from gui.ui_helpers import bloquear_columnas, configurar_ventana

class IngresoMasivoWindow:

    COLS = [
        ('codigo',         'Código / SKU',   90,  False),
        ('nombre',         'Nombre *',       180, True),
        ('descripcion',    'Descripción',    160, False),
        ('cantidad',       'Cantidad',        70, False),
        ('precio',         'Precio *',        80, True),
        ('stock_min',      'Stock Mín.',      70, False),
        ('proveedor',      'Proveedor',      130, False),
        ('categoria',      'Categoría',      110, False),
    ]

    def __init__(self, master, db, C, usuario, on_close=None):
        self.db        = db
        self.C         = C
        self.usuario   = usuario
        self.on_close  = on_close
        self._filas    = []   # lista de dicts con StringVar por campo
        self._widgets  = []   # lista de dicts con widgets Entry/Combobox

        self.win = tk.Toplevel(master)
        self.win.title("📋 Agregar varios productos")
        self.win.configure(bg=C['bg'])
        self.win.grab_set()
        configurar_ventana(self.win, size='main', min_width=1200, min_height=760, start_maximized=True)
        self.win.protocol("WM_DELETE_WINDOW", self._cerrar)

        # Datos para combos
        self._proveedores = [p['nombre'] for p in db.obtener_proveedores()]
        self._categorias  = db.obtener_nombres_categorias()

        self._build()
        # Empezar con 5 filas vacías
        for _ in range(5):
            self._agregar_fila()

    # ── Construcción de UI ────────────────────────────────────────────────────

    def _build(self):
        C = self.C

        # Encabezado
        hdr = tk.Frame(self.win, bg=C['header_bg'], height=50)
        hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr, text="📋  Agregar varios productos manualmente",
                 font=("Segoe UI", 13, "bold"),
                 bg=C['header_bg'], fg='white').pack(side=tk.LEFT, padx=16)
        # Barra de acciones
        bar = tk.Frame(self.win, bg=C['bg'])
        bar.pack(fill=tk.X, padx=14, pady=(10, 4))

        ttk.Button(bar, text="➕  Agregar fila",
                   command=self._agregar_fila,
                   style='Create.TButton').pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bar, text="🗑️  Borrar fila seleccionada",
                   command=self._borrar_fila,
                   style='Delete.TButton').pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bar, text="🔄  Limpiar todo",
                   command=self._limpiar_todo,
                   style='Neutral.TButton').pack(side=tk.LEFT)

        self.lbl_info = tk.Label(bar, text="",
                                  font=("Segoe UI", 9), bg=C['bg'],
                                  fg=C['muted'])
        self.lbl_info.pack(side=tk.LEFT, padx=14)

        ttk.Button(bar, text="💾  Guardar todos",
                   command=self._guardar,
                   style='Create.TButton').pack(side=tk.RIGHT)

        # Nota
        tk.Label(self.win,
                 text="  * Nombre y Precio son obligatorios. "
                      "Haz clic en una celda para editarla. "
                      "Proveedor y Categoría son selectores desplegables.",
                 font=("Segoe UI", 8), bg=C['bg'], fg=C['muted'],
                 anchor='w').pack(fill=tk.X, padx=14, pady=(0, 4))

        # Contenedor con scroll
        outer = tk.Frame(self.win, bg=C['bg'])
        outer.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))

        # Canvas para scroll horizontal y vertical
        self.canvas = tk.Canvas(outer, bg=C['bg'], highlightthickness=0)
        sb_y = ttk.Scrollbar(outer, orient=tk.VERTICAL,
                              command=self.canvas.yview)
        sb_x = ttk.Scrollbar(outer, orient=tk.HORIZONTAL,
                              command=self.canvas.xview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.configure(yscrollcommand=sb_y.set,
                              xscrollcommand=sb_x.set)

        # Frame interior donde van los widgets
        self.tabla_frame = tk.Frame(self.canvas, bg=C['bg'])
        self._win_id = self.canvas.create_window(
            (0, 0), window=self.tabla_frame, anchor='nw')
        self.tabla_frame.bind('<Configure>',
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',
            lambda e: self.canvas.itemconfig(self._win_id, width=e.width))
        self.canvas.bind_all('<MouseWheel>',
            lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))

        # Encabezados de columna
        self._build_headers()

    def _build_headers(self):
        C = self.C
        # Columna de número de fila
        tk.Label(self.tabla_frame, text="#",
                 font=("Segoe UI", 8, "bold"),
                 bg=C['primary'], fg='white',
                 width=3, relief='flat', padx=4, pady=6).grid(
            row=0, column=0, sticky='nsew', padx=1, pady=(0, 1))

        for ci, (_, label, _, _) in enumerate(self.COLS, start=1):
            bg = C['primary']
            tk.Label(self.tabla_frame, text=label,
                     font=("Segoe UI", 8, "bold"),
                     bg=bg, fg='white',
                     relief='flat', padx=6, pady=6).grid(
                row=0, column=ci, sticky='nsew', padx=1, pady=(0, 1))

    # ── Gestión de filas ──────────────────────────────────────────────────────

    def _agregar_fila(self, datos=None):
        """Agrega una fila editable al final de la tabla."""
        C   = self.C
        num = len(self._filas) + 1
        row = num  # row 0 es el encabezado

        fila_vars = {}
        fila_wgts = {}

        # Número de fila
        lbl_num = tk.Label(self.tabla_frame, text=str(num),
                           font=("Segoe UI", 8),
                           bg=C['surface'], fg=C['muted'],
                           width=3, padx=4, pady=4)
        lbl_num.grid(row=row, column=0, sticky='nsew', padx=1, pady=1)
        fila_wgts['_num'] = lbl_num

        for ci, (key, _, width, requerido) in enumerate(self.COLS, start=1):
            var = tk.StringVar(value=datos.get(key, '') if datos else '')
            fila_vars[key] = var

            if key == 'proveedor':
                w = ttk.Combobox(self.tabla_frame, textvariable=var,
                                  values=self._proveedores,
                                  width=width // 7, state='normal')
            elif key == 'categoria':
                w = ttk.Combobox(self.tabla_frame, textvariable=var,
                                  values=self._categorias,
                                  width=width // 7, state='normal')
            else:
                w = ttk.Entry(self.tabla_frame, textvariable=var,
                              width=width // 7)

            # Resaltar campos obligatorios con borde
            if requerido:
                w.configure(style='TEntry')

            w.grid(row=row, column=ci, sticky='nsew', padx=1, pady=1,
                   ipady=3)
            fila_wgts[key] = w

            # Tab entre celdas
            w.bind('<Tab>',      lambda e, r=row, c=ci: self._tab_siguiente(r, c))
            w.bind('<Return>',   lambda e, r=row: self._enter_fila(r))

        self._filas.append(fila_vars)
        self._widgets.append(fila_wgts)

        # Actualizar contador
        self._actualizar_info()

        # Scroll al fondo para ver la nueva fila
        self.win.after(50, lambda: self.canvas.yview_moveto(1.0))

        # Foco en el primer campo de la nueva fila
        self.win.after(60, lambda: fila_wgts['codigo'].focus())

    def _borrar_fila(self):
        """Borra la última fila o la que tenga foco."""
        if not self._filas:
            return
        # Buscar qué fila tiene el foco
        foco = self.win.focus_get()
        fila_idx = None
        for i, wgts in enumerate(self._widgets):
            if foco in wgts.values():
                fila_idx = i
                break
        if fila_idx is None:
            fila_idx = len(self._filas) - 1  # última por defecto

        # Destruir widgets de esa fila
        for w in self._widgets[fila_idx].values():
            w.destroy()
        self._filas.pop(fila_idx)
        self._widgets.pop(fila_idx)

        # Reasignar números de fila
        for i, wgts in enumerate(self._widgets):
            wgts['_num'].config(text=str(i + 1))
            # Mover al row correcto (i+1 por el encabezado)
            for key, w in wgts.items():
                info = w.grid_info()
                if info:
                    w.grid(row=i + 1)

        self._actualizar_info()

    def _limpiar_todo(self):
        if self._filas and not messagebox.askyesno(
                "🔄 Limpiar", "¿Borrar todas las filas?",
                parent=self.win):
            return
        for wgts in self._widgets:
            for w in wgts.values():
                w.destroy()
        self._filas.clear()
        self._widgets.clear()
        self._actualizar_info()
        for _ in range(5):
            self._agregar_fila()

    def _tab_siguiente(self, row, col):
        """Tab mueve al siguiente campo."""
        max_col = len(self.COLS)
        next_col = col + 1
        next_row = row
        if next_col > max_col:
            next_col = 1
            next_row = row + 1
            if next_row > len(self._filas):
                self._agregar_fila()
                return 'break'
        # Buscar widget en (next_row, next_col)
        for wgts in self._widgets:
            for w in wgts.values():
                info = w.grid_info()
                if info.get('row') == next_row and info.get('column') == next_col:
                    w.focus()
                    return 'break'
        return 'break'

    def _enter_fila(self, row):
        """Enter en la última fila agrega una nueva."""
        if row == len(self._filas):
            self._agregar_fila()
        return 'break'

    def _actualizar_info(self):
        n = len(self._filas)
        self.lbl_info.config(text=f"{n} fila(s)")

  