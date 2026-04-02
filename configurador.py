"""
configurador.py — Pantalla de configuración de conexión a MySQL.

Se muestra automáticamente cuando:
  - Es la primera instalación (config.json no existe)
  - La conexión a MySQL falla al arrancar
  - El usuario lo abre desde Administración > Config. Sistema

Guarda la configuración en config.json (no modifica config.py).
Al confirmar: prueba la conexión, crea la BD y las tablas si no existen.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from gui.ui_helpers import configurar_ventana

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db_config.json')

DEFAULTS = {
    'host':     'localhost',
    'port':     '3306',
    'user':     'root',
    'password': '',
    'database': 'inventario_sts',
}


def cargar_config():
    """Retorna config guardada o defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                # Fusionar con defaults por si faltan claves
                return {**DEFAULTS, **data}
        except Exception:
            pass
    return DEFAULTS.copy()


def guardar_config(cfg):
    """Guarda config en db_config.json."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)


def es_primera_instalacion():
    """True si no existe el archivo de configuración."""
    return not os.path.exists(CONFIG_FILE)


# ── Colores ───────────────────────────────────────────────────────────────────
C = {
    'bg':       '#0F172A',
    'card':     '#1E293B',
    'accent':   '#00B4BC',
    'accent2':  '#1A6FD4',
    'text':     '#E2F0FF',
    'muted':    '#7BA7CC',
    'border':   '#334155',
    'success':  '#059669',
    'danger':   '#EF4444',
    'warning':  '#F59E0B',
}


class ConfiguradorDB:
    """
    Ventana de configuración de base de datos.
    Retorna True si la configuración fue guardada y la BD inicializada.
    """

    def __init__(self, master, motivo='primera_instalacion'):
        self.master   = master
        self.motivo   = motivo
        self.exitoso  = False
        self._db      = None

        self.win = tk.Toplevel(master)
        self.win.title("⚙️ Configuración de Base de Datos — Inventoryx")
        self.win.grab_set()
        self.win.configure(bg=C['bg'])
        self.win.protocol("WM_DELETE_WINDOW", self._cerrar)
        configurar_ventana(
            self.win,
            width=760,
            height=560,
            min_width=720,
            min_height=500,
            resizable=(True, False),
        )

        self._build()
        self._cargar_valores()

    def _build(self):
        # ── Encabezado (fijo arriba) ──────────────────────────────────────────
        hdr = tk.Frame(self.win, bg='#0D1F3C', height=70)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙️  Configuración de Base de Datos",
                 font=("Segoe UI", 13, "bold"),
                 bg='#0D1F3C', fg=C['text']).pack(side=tk.LEFT, padx=20, pady=18)

        # ── Pie fijo (botones + progreso + estado) — se empaca ANTES del body
        pie = tk.Frame(self.win, bg=C['bg'])
        pie.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)

        # Barra progreso
        self.progress = ttk.Progressbar(pie, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=24, pady=(0, 2))

        # Estado de conexión
        self.lbl_estado = tk.Label(pie, text="",
                                   font=("Segoe UI", 8),
                                   bg=C['bg'], fg=C['muted'],
                                   wraplength=670, justify='left')
        self.lbl_estado.pack(fill=tk.X, padx=24, pady=(0, 2))

        # Nota informativa
        tk.Label(pie,
                 text="ℹ️  El sistema creará la base de datos y las tablas automáticamente "
                      "si no existen. No se borrarán datos existentes.",
                 font=("Segoe UI", 8),
                 bg=C['bg'], fg=C['muted'],
                 justify='left').pack(anchor='w', padx=24, pady=(0, 6))

        # Separador
        tk.Frame(pie, bg=C['border'], height=1).pack(fill=tk.X)

        # Botones
        frm_bot = tk.Frame(pie, bg=C['bg'])
        frm_bot.pack(fill=tk.X, padx=24, pady=12)

        self.btn_probar = tk.Button(
            frm_bot, text="🔌 Probar Conexión",
            font=("Segoe UI", 10),
            bg=C['accent2'], fg='white',
            relief='flat', cursor='hand2', padx=16, pady=8,
            activebackground='#1558A8', activeforeground='white',
            command=self._probar)
        self.btn_probar.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_confirmar = tk.Button(
            frm_bot, text="✅ Confirmar y Guardar",
            font=("Segoe UI", 10, "bold"),
            bg=C['success'], fg='white',
            relief='flat', cursor='hand2', padx=16, pady=8,
            activebackground='#047857', activeforeground='white',
            state='disabled',
            command=self._confirmar)
        self.btn_confirmar.pack(side=tk.LEFT, padx=(0, 8))

        if self.motivo == 'manual':
            tk.Button(frm_bot, text="Cancelar",
                      font=("Segoe UI", 10),
                      bg=C['card'], fg=C['muted'],
                      relief='flat', cursor='hand2', padx=16, pady=8,
                      command=self._cerrar).pack(side=tk.LEFT)

        # ── Body central (scroll si hace falta) ───────────────────────────────
        body = tk.Frame(self.win, bg=C['bg'])
        body.pack(fill=tk.BOTH, expand=True, padx=24, pady=12)

        # Motivo / banner
        motivos = {
            'primera_instalacion': ("🎉 Primera instalación",
                                     "Configure la conexión a MySQL para inicializar el sistema."),
            'fallo_conexion':       ("❌ Error de conexión",
                                     "No se pudo conectar. Verifique los datos e intente de nuevo."),
            'manual':               ("⚙️ Reconfigurar",
                                     "Modifique la conexión a MySQL según sea necesario."),
        }
        titulo_mot, desc_mot = motivos.get(self.motivo, motivos['manual'])
        color_banner = C['warning'] if self.motivo == 'fallo_conexion' else C['accent2']
        banner = tk.Frame(body, bg=color_banner, pady=8, padx=14)
        banner.pack(fill=tk.X, pady=(0, 14))
        tk.Label(banner, text=titulo_mot,
                 font=("Segoe UI", 10, "bold"),
                 bg=color_banner, fg='white').pack(anchor='w')
        tk.Label(banner, text=desc_mot,
                 font=("Segoe UI", 9),
                 bg=color_banner, fg='white').pack(anchor='w')

        # ── Formulario 2 columnas ─────────────────────────────────────────────
        card = tk.Frame(body, bg=C['card'], padx=20, pady=14)
        card.pack(fill=tk.X)
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        def _campo(parent, label, attr, es_pass, placeholder, row, col, colspan=1):
            tk.Label(parent, text=label,
                     font=("Segoe UI", 8, "bold"),
                     bg=C['card'], fg=C['muted'],
                     anchor='w').grid(row=row*2, column=col, columnspan=colspan,
                                      sticky='w',
                                      padx=(0 if col==0 else 12, 0),
                                      pady=(8 if row > 0 else 0, 2))
            frm_e = tk.Frame(parent, bg=C['accent'], pady=1)
            frm_e.grid(row=row*2+1, column=col, columnspan=colspan,
                       sticky='ew', padx=(0 if col==0 else 12, 0))
            frm_i = tk.Frame(frm_e, bg=C['border'])
            frm_i.pack(fill=tk.X, padx=1, pady=1)
            e = tk.Entry(frm_i,
                         font=("Segoe UI", 10),
                         bg=C['border'], fg=C['text'],
                         insertbackground=C['accent'],
                         relief='flat', bd=-2,
                         show='*' if es_pass else '')
            e.pack(fill=tk.X)
            if placeholder and not es_pass:
                e.insert(0, placeholder)
                e.config(fg=C['muted'])
                def _fi(event, entry=e, ph=placeholder):
                    if entry.get() == ph:
                        entry.delete(0, tk.END); entry.config(fg=C['text'])
                def _fo(event, entry=e, ph=placeholder):
                    if not entry.get():
                        entry.insert(0, ph); entry.config(fg=C['muted'])
                e.bind('<FocusIn>', _fi); e.bind('<FocusOut>', _fo)
            e.bind('<FocusIn>',  lambda ev, f=frm_e: f.config(bg=C['accent']))
            e.bind('<FocusOut>', lambda ev, f=frm_e: f.config(bg=C['border']))
            setattr(self, attr, e)

        _campo(card, "Servidor (Host)", 'e_host', False, "localhost  o  192.168.1.100", 0, 0)
        _campo(card, "Puerto",          'e_port', False, "3306",                          0, 1)
        _campo(card, "Usuario MySQL",   'e_user', False, "root",                          1, 0)
        _campo(card, "Contraseña MySQL",'e_pass', True,  "",                              1, 1)
        _campo(card, "Nombre de la base de datos", 'e_db', False, "inventario_sts",       2, 0, colspan=2)

        frm_show = tk.Frame(card, bg=C['card'])
        frm_show.grid(row=6, column=0, columnspan=2, sticky='w', pady=(8, 0))
        self.var_show = tk.BooleanVar(value=False)
        tk.Checkbutton(frm_show, text="Mostrar contraseña",
                       variable=self.var_show,
                       command=self._toggle_pass,
                       bg=C['card'], fg=C['muted'],
                       selectcolor=C['border'],
                       activebackground=C['card'],
                       font=("Segoe UI", 8)).pack(side=tk.LEFT)

    def _cargar_valores(self):
        cfg = cargar_config()
        for attr, key in [('e_host', 'host'), ('e_port', 'port'),
                           ('e_user', 'user'), ('e_pass', 'password'),
                           ('e_db',   'database')]:
            w = getattr(self, attr)
            w.delete(0, tk.END)
            w.insert(0, cfg.get(key, ''))
            w.config(fg=C['text'])

    def _toggle_pass(self):
        self.e_pass.config(show='' if self.var_show.get() else '*')

    def _get_config(self):
        return {
            'host':     self.e_host.get().strip(),
            'port':     self.e_port.get().strip() or '3306',
            'user':     self.e_user.get().strip(),
            'password': self.e_pass.get(),
            'database': self.e_db.get().strip(),
        }

    def _set_estado(self, msg, color=None):
        self.lbl_estado.config(text=msg,
                                fg=color or C['muted'])
        self.win.update()

    def _probar(self):
        cfg = self._get_config()
        if not cfg['host'] or not cfg['user'] or not cfg['database']:
            self._set_estado("⚠️  Complete los campos obligatorios.", C['warning'])
            return

        self._set_estado("⏳  Conectando a MySQL...", C['muted'])
        self.progress.start(10)
        self.btn_probar.config(state='disabled')
        self.btn_confirmar.config(state='disabled')
        self.win.update()

        try:
            import mysql.connector
            # Probar sin especificar BD primero (puede que no exista aún)
            conn = mysql.connector.connect(
                host=cfg['host'],
                port=int(cfg['port']),
                user=cfg['user'],
                password=cfg['password'],
                connection_timeout=8)
            conn.close()
            self.progress.stop()
            self._set_estado(
                f"✅  Conexión exitosa a MySQL en {cfg['host']}:{cfg['port']}.\n"
                f"   La base de datos '{cfg['database']}' se creará si no existe.",
                C['success'])
            self.btn_confirmar.config(state='normal')
            self.btn_probar.config(state='normal')
            self._cfg_probada = cfg

        except Exception as e:
            self.progress.stop()
            self.btn_probar.config(state='normal')
            err = str(e)
            if '2003' in err or 'Can\'t connect' in err:
                msg = (f"❌  No se pudo conectar a {cfg['host']}:{cfg['port']}.\n"
                       f"   Verifique que MySQL esté corriendo y que el host sea correcto.")
            elif '1045' in err or 'Access denied' in err:
                msg = (f"❌  Acceso denegado para '{cfg['user']}'.\n"
                       f"   Verifique el usuario y contraseña de MySQL.")
            else:
                msg = f"❌  Error: {err}"
            self._set_estado(msg, C['danger'])

    def _confirmar(self):
        if not hasattr(self, '_cfg_probada'):
            self._set_estado("⚠️  Primero pruebe la conexión.", C['warning'])
            return

        cfg = self._cfg_probada

        try:
            import mysql.connector

            # ── Verificar si la BD ya existe ──────────────────────────────────
            conn = mysql.connector.connect(
                host=cfg['host'],
                port=int(cfg['port']),
                user=cfg['user'],
                password=cfg['password'],
                connection_timeout=8)
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES LIKE %s", (cfg['database'],))
            bd_existe = cursor.fetchone() is not None
            cursor.close()
            conn.close()

            # Si NO existe → advertir SOLO si no es primera instalación
            # (en primera instalación es normal que la BD no exista aún)
            if not bd_existe and self.motivo != 'primera_instalacion':
                confirmar = messagebox.askyesno(
                    "⚠️ Base de datos nueva",
                    f"La base de datos \"{cfg['database']}\" no existe todavía.\n\n"
                    f"Si continúa, se creará vacía — sin productos, usuarios\n"
                    f"ni historial.\n\n"
                    f"Si desea conservar sus datos actuales:\n"
                    f"  1. Cancele esta ventana\n"
                    f"  2. Vaya a Backups → Backup y Restauración\n"
                    f"  3. Cree un backup de la base actual\n"
                    f"  4. Vuelva aquí y confirme\n"
                    f"  5. Restaure el backup desde la nueva BD\n\n"
                    f"¿Desea continuar y crear la base de datos vacía?",
                    icon='warning',
                    parent=self.win)
                if not confirmar:
                    self._set_estado(
                        "ℹ️  Cancelado. Vaya a Backups → Backup y Restauración "
                        "para respaldar sus datos antes de continuar.",
                        C['warning'])
                    return

        except Exception as e:
            self._set_estado(f"❌  Error al verificar BD: {e}", C['danger'])
            return

        # ── Proceder a crear/inicializar ──────────────────────────────────────
        self._set_estado("⏳  Creando base de datos y tablas...", C['muted'])
        self.progress.start(10)
        self.btn_confirmar.config(state='disabled')
        self.win.update()

        try:
            import mysql.connector

            # Crear BD si no existe
            conn = mysql.connector.connect(
                host=cfg['host'],
                port=int(cfg['port']),
                user=cfg['user'],
                password=cfg['password'],
                connection_timeout=8)
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            cursor.close()
            conn.close()

            # Guardar configuración
            guardar_config(cfg)

            # Actualizar config.py en memoria para que DatabaseManager lo use
            import config
            config.DB_CONFIG['host']     = cfg['host']
            config.DB_CONFIG['port']     = int(cfg['port'])
            config.DB_CONFIG['user']     = cfg['user']
            config.DB_CONFIG['password'] = cfg['password']
            config.DB_CONFIG['database'] = cfg['database']

            # Crear tablas usando DatabaseManager
            from database import DatabaseManager
            db = DatabaseManager()
            if db.connect():
                db.create_tables()
                db.disconnect()
                self._db = None

            self.progress.stop()
            self._set_estado(
                f"✅  Configuración guardada.\n"
                f"   Base de datos '{cfg['database']}' inicializada correctamente.",
                C['success'])

            self.win.after(1200, self._finalizar)

        except Exception as e:
            self.progress.stop()
            self.btn_confirmar.config(state='normal')
            self._set_estado(f"❌  Error al inicializar: {e}", C['danger'])

    def _finalizar(self):
        self.exitoso = True
        self.win.destroy()

    def _cerrar(self):
        if not self.exitoso and self.motivo != 'manual':
            if not messagebox.askyesno(
                    "⚠️ Salir",
                    "Sin configuración el sistema no puede funcionar.\n"
                    "¿Desea salir del programa?",
                    parent=self.win):
                return
        self.win.destroy()


def mostrar_configurador(master, motivo='primera_instalacion'):
    """Abre el configurador y retorna True si se configuró exitosamente."""
    cfg = ConfiguradorDB(master, motivo=motivo)
    master.wait_window(cfg.win)
    return cfg.exitoso
