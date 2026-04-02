import tkinter as tk
from tkinter import ttk, messagebox
from gui.ui_helpers import configurar_ventana

# ── Definición de todos los campos opcionales ─────────────────────────────────
CAMPOS_OPCIONALES = [
    {
        'key':        'codigo_barras',
        'label':      'Código de Barras / EAN',
        'desc':       'Código de barras EAN-13 o cualquier código de escaneo.',
        'col_sql':    'codigo_barras VARCHAR(100) DEFAULT NULL',
        'tipo_form':  'entry',
        'col_tabla':  'C. Barras',
        'ancho':      110,
    },
    {
        'key':        'marca',
        'label':      'Marca / Fabricante',
        'desc':       'Marca comercial o fabricante del producto.',
        'col_sql':    'marca VARCHAR(100) DEFAULT NULL',
        'tipo_form':  'entry',
        'col_tabla':  'Marca',
        'ancho':      100,
    },
    {
        'key':        'modelo',
        'label':      'Modelo',
        'desc':       'Número o nombre de modelo del producto.',
        'col_sql':    'modelo VARCHAR(100) DEFAULT NULL',
        'tipo_form':  'entry',
        'col_tabla':  'Modelo',
        'ancho':      100,
    },
    {
        'key':        'color',
        'label':      'Color',
        'desc':       'Color principal del producto.',
        'col_sql':    'color VARCHAR(60) DEFAULT NULL',
        'tipo_form':  'entry',
        'col_tabla':  'Color',
        'ancho':      80,
    },
    {
        'key':        'peso',
        'label':      'Peso (kg)',
        'desc':       'Peso del producto en kilogramos.',
        'col_sql':    'peso DECIMAL(10,3) DEFAULT NULL',
        'tipo_form':  'entry',
        'col_tabla':  'Peso',
        'ancho':      70,
    },
    {
        'key':        'ubicacion',
        'label':      'Ubicación en Bodega',
        'desc':       'Código de ubicación física (ej. A-12, Estante 3-B).',
        'col_sql':    'ubicacion VARCHAR(100) DEFAULT NULL',
        'tipo_form':  'entry',
        'col_tabla':  'Ubicación',
        'ancho':      100,
    },
    {
        'key':        'numero_serie',
        'label':      'Número de Serie',
        'desc':       'Número de serie único del producto o lote.',
        'col_sql':    'numero_serie VARCHAR(150) DEFAULT NULL',
        'tipo_form':  'entry',
        'col_tabla':  'N. Serie',
        'ancho':      110,
    },
    {
        'key':        'garantia_meses',
        'label':      'Garantía (meses)',
        'desc':       'Tiempo de garantía del fabricante en meses.',
        'col_sql':    'garantia_meses INT DEFAULT NULL',
        'tipo_form':  'entry',
        'col_tabla':  'Garantía',
        'ancho':      80,
    },
    {
        'key':        'fecha_vence',
        'label':      'Fecha de Vencimiento',
        'desc':       'Fecha de vencimiento (YYYY-MM-DD). Para alimentos, medicamentos, etc.',
        'col_sql':    'fecha_vence DATE DEFAULT NULL',
        'tipo_form':  'entry',
        'col_tabla':  'Vencimiento',
        'ancho':      100,
    },
    {
        'key':        'impuesto_pct',
        'label':      'ITBIS / Impuesto %',
        'desc':       'Porcentaje de impuesto aplicable al producto.',
        'col_sql':    'impuesto_pct DECIMAL(5,2) DEFAULT NULL',
        'tipo_form':  'entry',
        'col_tabla':  'Impuesto%',
        'ancho':      90,
    },
]

CAMPOS_MAP = {c['key']: c for c in CAMPOS_OPCIONALES}


def obtener_campos_activos(db):
    """Retorna lista de dicts de campos opcionales activos."""
    activos = []
    for c in CAMPOS_OPCIONALES:
        val = db.get_config(f"campo_opt_{c['key']}", '0')
        if val == '1':
            activos.append(c)
    return activos


def asegurar_columnas(db):
    """Crea en la BD las columnas de los campos activos si no existen."""
    activos = obtener_campos_activos(db)
    for c in activos:
        key = c['key']
        col_sql = c['col_sql']
        col_name = key
        try:
            db.cursor.execute(
                f"ALTER TABLE productos ADD COLUMN `{col_name}` {col_sql.split(' ', 1)[1]}")
            db.connection.commit()
            print(f"[OK] Columna opcional creada: {col_name}")
        except Exception:
            pass  # Ya existe


# ── Ventana de configuración ──────────────────────────────────────────────────

class CamposOpcionalesWindow:

    def __init__(self, master, db, C, usuario):
        self.db      = db
        self.C       = C
        self.usuario = usuario
        self._vars   = {}

        self.win = tk.Toplevel(master)
        self.win.title("🔧 Campos Opcionales de Productos")
        self.win.configure(bg=C['bg'])
        self.win.grab_set()
        configurar_ventana(self.win, width=860, height=760, min_width=760, min_height=620)
        self._build()

    def _build(self):
        C = self.C

        # Encabezado
        hdr = tk.Frame(self.win, bg=C['header_bg'], height=50)
        hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr, text="🔧  Campos Opcionales de Productos",
                 font=("Segoe UI", 12, "bold"),
                 bg=C['header_bg'], fg='white').pack(side=tk.LEFT, padx=16)
        ttk.Label(self.win,
                  text="Active los campos que desea mostrar en el formulario, "
                       "tabla y exportaciones de productos.\n"
                       "Los cambios aplican al recargar la sección de Inventario.",
                  foreground=C['muted'], wraplength=640,
                  justify='left').pack(padx=16, pady=(10, 4), anchor='w')

        # Tabla de campos
        frm = ttk.LabelFrame(self.win, text="Campos disponibles", padding=10)
        frm.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))

        # Encabezado de columnas
        hdr_frm = tk.Frame(frm, bg=C['primary'])
        hdr_frm.pack(fill=tk.X, pady=(0, 4))
        for txt, w in [("Activo", 60), ("Campo", 180), ("Descripción", 360)]:
            tk.Label(hdr_frm, text=txt,
                     font=("Segoe UI", 8, "bold"),
                     bg=C['primary'], fg='white',
                     width=w//7, anchor='w',
                     padx=6, pady=4).pack(side=tk.LEFT)

        # Scroll
        canvas = tk.Canvas(frm, bg=C['bg'], highlightthickness=0)
        sb = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=C['bg'])
        canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>',
                   lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        for i, campo in enumerate(CAMPOS_OPCIONALES):
            key = campo['key']
            val_actual = self.db.get_config(f"campo_opt_{key}", '0')
            var = tk.BooleanVar(value=(val_actual == '1'))
            self._vars[key] = var

            row_bg = C['surface'] if i % 2 == 0 else C['bg']
            row = tk.Frame(inner, bg=row_bg)
            row.pack(fill=tk.X, pady=1)

            # Checkbox
            tk.Checkbutton(row, variable=var,
                           bg=row_bg,
                           activebackground=row_bg,
                           cursor='hand2').pack(side=tk.LEFT, padx=(8, 4))

            # Label campo
            tk.Label(row, text=campo['label'],
                     font=("Segoe UI", 9, "bold"),
                     bg=row_bg, fg=C['text'],
                     width=22, anchor='w').pack(side=tk.LEFT, padx=(0, 8))

            # Descripción
            tk.Label(row, text=campo['desc'],
                     font=("Segoe UI", 8),
                     bg=row_bg, fg=C['muted'],
                     anchor='w', wraplength=320,
                     justify='left').pack(side=tk.LEFT, fill=tk.X, expand=True,
                                          padx=(0, 8), pady=4)

        # Botones inferiores
        frm_bot = ttk.Frame(self.win)
        frm_bot.pack(fill=tk.X, padx=16, pady=(0, 12))

        ttk.Button(frm_bot, text="✅ Guardar cambios",
                   command=self._guardar,
                   style='Create.TButton').pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(frm_bot, text="Cancelar",
                   command=self.win.destroy,
                   style='Neutral.TButton').pack(side=tk.RIGHT)

        lbl_info = tk.Label(frm_bot,
                            text="ℹ️  Los campos activos se agregan automáticamente a la base de datos.",
                            font=("Segoe UI", 8),
                            bg=C['bg'], fg=C['muted'])
        lbl_info.pack(side=tk.LEFT)

    def _guardar(self):
        cambios = 0
        for key, var in self._vars.items():
            nuevo_val = '1' if var.get() else '0'
            viejo_val = self.db.get_config(f"campo_opt_{key}", '0')
            self.db.set_config(f"campo_opt_{key}", nuevo_val)
            if nuevo_val != viejo_val:
                cambios += 1

        # Crear columnas en BD para los campos activos nuevos
        asegurar_columnas(self.db)

        self.db.registrar_log(
            self.usuario['id'], self.usuario['username'],
            'Campos opcionales', f'{cambios} campo(s) modificado(s)')

        messagebox.showinfo(
            "✅ Guardado",
            f"Configuración guardada.\n"
            f"{cambios} campo(s) modificado(s).\n\n"
            f"Recarga la sección de Inventario para ver los cambios.",
            parent=self.win)
        self.win.destroy()
