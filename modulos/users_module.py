from gui.estilos import ventana_fullscreen
import tkinter as tk
from tkinter import ttk, messagebox
from database import TODOS_LOS_PERMISOS
from gui.ui_helpers import bloquear_columnas, configurar_ventana, pedir_confirmacion_password


DEFAULT_THEME = {
    'bg': '#F1F5F9',
    'surface': '#FFFFFF',
    'text': '#1E293B',
    'primary': '#2563EB',
    'secondary': '#3B82F6',
    'danger': '#EF4444',
    'warning': '#F59E0B',
    'header_bg': '#1E3A5F',
    'muted': '#64748B',
}


def _theme(C=None):
    theme = DEFAULT_THEME.copy()
    if C:
        theme.update({k: v for k, v in C.items() if v is not None})
    return theme


def _pedir_password(master, db, id_usuario, titulo, C=None):
    C = _theme(C)
    return pedir_confirmacion_password(
        master, db, id_usuario, titulo,
        "Ingrese su contraseña para confirmar esta acción.",
        bg=C['bg'],
        geometry='360x200')


def _abrir_reporte_actividad(master, db, C=None):
    """Muestra un resumen consolidado de actividad por usuario."""
    C = _theme(C)
    win = tk.Toplevel(master)
    win.title("📊 Actividad por Usuario")
    win.configure(bg=C['bg'])
    win.grab_set()
    configurar_ventana(win, width=940, height=620, min_width=820, min_height=520)

    tk.Label(win, text="📊 Actividad por Usuario",
             font=('Segoe UI', 13, 'bold'),
             bg=C['bg'], fg=C['primary']).pack(pady=10)

    frm = ttk.Frame(win)
    frm.pack(fill=tk.BOTH, expand=True, padx=12)
    sb = ttk.Scrollbar(frm)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    cols = ('Usuario', 'Nombre', 'Rol', 'Movimientos', 'Acciones Log', 'Último Login', 'Estado')
    tree = ttk.Treeview(frm, columns=cols, show='headings', yscrollcommand=sb.set, height=14)
    sb.config(command=tree.yview)
    for c_, w_ in zip(cols, (110, 160, 100, 100, 100, 140, 80)):
        tree.heading(c_, text=c_)
        tree.column(c_, width=w_)
    tree.tag_configure('inactivo', foreground=C['danger'])

    for u in db.obtener_resumen_actividad_usuarios():
        ultimo = str(u.get('ultimo_login', ''))[:16] if u.get('ultimo_login') else 'Nunca'
        tag = '' if u['activo'] else 'inactivo'
        tree.insert('', tk.END, tags=(tag,), values=(
            u['username'],
            u['nombre_completo'] or '',
            u['rol'],
            u.get('movimientos', 0),
            u.get('acciones_log', 0),
            ultimo,
            '✅ Activo' if u['activo'] else '🚫 Inhabilitado'))
    tree.pack(fill=tk.BOTH, expand=True)


class UsersWindow:
    """
    Gestión de usuarios.
    - Crear / Actualizar datos y contraseña
    - Inhabilitar usuario (bloquea acceso sin borrar nada)
    - Habilitar usuario  (reactiva el acceso)
    No hay botón Eliminar — los usuarios se inhabilitan para preservar
    el historial de movimientos y auditoría.
    """

    def __init__(self, master, db, usuario_actual, C=None):
        self.db             = db
        self.usuario_actual = usuario_actual
        self.seleccionado   = None
        self.C              = _theme(C)

        self.win = ventana_fullscreen(master, "👤 Gestionar Usuarios",
                                       self.C)
        self._build()
        self._cargar()

    def _build(self):
        C = self.C

        hdr = tk.Frame(self.win, bg=C['header_bg'], height=50)
        hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr, text="👤  Gestión de Usuarios",
                 font=("Segoe UI", 13, "bold"),
                 bg=C['header_bg'], fg='white').pack(side=tk.LEFT, padx=16)
        body = tk.Frame(self.win, bg=C['bg'])
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        paned = ttk.PanedWindow(body, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # ── Lista ──────────────────────────────────────────────────────────────
        frm_l = ttk.LabelFrame(paned, text="Usuarios registrados", padding=8)
        paned.add(frm_l, weight=3)

        sb = ttk.Scrollbar(frm_l); sb.pack(side=tk.RIGHT, fill=tk.Y)
        cols = ('ID', 'Usuario', 'Nombre', 'Rol', 'Estado', 'Creado', 'Último Login', 'Movimientos')
        self.tree = ttk.Treeview(frm_l, columns=cols, show='headings',
                                  yscrollcommand=sb.set, height=22)
        sb.config(command=self.tree.yview)
        for c, w in zip(cols, (40, 110, 180, 110, 90, 110, 130, 90)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, minwidth=w,
                              anchor=tk.CENTER if c in ('ID', 'Estado') else tk.W)
        self.tree.tag_configure('activo', background=C['surface'], foreground=C['secondary'])
        self.tree.tag_configure('inhabilitado', background=C['surface'], foreground=C['danger'])
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(self.tree)
        self.tree.bind('<<TreeviewSelect>>', self._seleccionar)

        ttk.Button(frm_l, text="📊 Reporte de Actividad por Usuario",
                   command=self._reporte_actividad).pack(pady=(6, 0))

        # ── Formulario ─────────────────────────────────────────────────────────
        frm_r = ttk.LabelFrame(paned, text="Datos del usuario", padding=10)
        paned.add(frm_r, weight=2)

        roles         = self.db.obtener_roles()
        self._roles   = {r['nombre']: r['id'] for r in roles}
        nombres_roles = list(self._roles.keys())

        campos = [
            ("Usuario:",         'e_username', 'entry'),
            ("Contraseña:",      'e_password', 'pass'),
            ("Nombre completo:", 'e_nombre',   'entry'),
            ("Rol:",             'e_rol',       'combo'),
        ]
        for i, (lbl, attr, tipo) in enumerate(campos):
            ttk.Label(frm_r, text=lbl).grid(row=i, column=0, sticky='w',
                                             padx=(0, 8), pady=6)
            if tipo == 'combo':
                w = ttk.Combobox(frm_r, values=nombres_roles,
                                  width=18, state='readonly')
                if nombres_roles: w.set(nombres_roles[0])
            elif tipo == 'pass':
                w = ttk.Entry(frm_r, width=20, show='*')
            else:
                w = ttk.Entry(frm_r, width=20)
            w.grid(row=i, column=1, pady=6, sticky='ew')
            setattr(self, attr, w)

        ttk.Label(frm_r, text="(Vacío = no cambiar contraseña)",
                  font=('Segoe UI', 8), foreground=C['muted']).grid(
            row=5, column=0, columnspan=2, sticky='w')

        # Nota explicativa
        tk.Label(frm_r,
                 text="ℹ️  Los usuarios se inhabilitan en lugar de\n"
                      "   eliminarse para preservar el historial.",
                 font=('Segoe UI', 8), bg=C['bg'], fg=C['muted'],
                 justify='left').grid(row=6, column=0, columnspan=2,
                                      sticky='w', pady=(8, 0))

        frm_btn = ttk.Frame(frm_r)
        frm_btn.grid(row=7, column=0, columnspan=2, pady=14, sticky='ew')

        ttk.Button(frm_btn, text="➕ Crear",
                   command=self._crear,
                   style='Create.TButton').pack(side=tk.LEFT, padx=3,
                                                expand=True, fill=tk.X)
        ttk.Button(frm_btn, text="✏️ Actualizar",
                   command=self._actualizar,
                   style='Update.TButton').pack(side=tk.LEFT, padx=3,
                                                expand=True, fill=tk.X)
        ttk.Button(frm_btn, text="🚫 Inhabilitar",
                   command=self._inhabilitar,
                   style='Delete.TButton').pack(side=tk.LEFT, padx=3,
                                                expand=True, fill=tk.X)
        ttk.Button(frm_btn, text="✅ Habilitar",
                   command=self._habilitar,
                   style='Neutral.TButton').pack(side=tk.LEFT, padx=3,
                                                  expand=True, fill=tk.X)
        ttk.Button(frm_btn, text="🔄",
                   command=self._limpiar,
                   style='Neutral.TButton').pack(side=tk.LEFT, padx=3)

        ttk.Button(frm_r, text="🔑 Resetear Contraseña (Admin)",
                   command=self._resetear_password_admin,
                   style='Warn.TButton').grid(row=8, column=0, columnspan=2,
                                               pady=(6, 0), sticky='ew')

    def _cargar(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for u in self.db.obtener_resumen_actividad_usuarios():
            activo = u['activo']
            estado = '✅ Activo' if activo else '🚫 Inhabilitado'
            tag    = 'activo' if activo else 'inhabilitado'
            ultimo = str(u.get('ultimo_login',''))[:16] if u.get('ultimo_login') else 'Nunca'
            self.tree.insert('', tk.END, tags=(tag,), values=(
                u['id'], u['username'], u['nombre_completo'] or '',
                u['rol'], estado,
                str(u['fecha_creacion'])[:10] if u['fecha_creacion'] else '',
                ultimo, u.get('movimientos', 0)))

    def _seleccionar(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])['values']
        self.seleccionado = vals[0]
        self.e_username.delete(0, tk.END); self.e_username.insert(0, vals[1])
        self.e_nombre.delete(0, tk.END);   self.e_nombre.insert(0, vals[2])
        self.e_rol.set(vals[3])
        self.e_password.delete(0, tk.END)

    def _crear(self):
        usr = self.e_username.get().strip()
        pwd = self.e_password.get()
        nom = self.e_nombre.get().strip()
        rol = self.e_rol.get()
        if not usr or not pwd or not rol:
            messagebox.showwarning("⚠️", "Usuario, contraseña y rol son requeridos.",
                                   parent=self.win); return
        ok, msg = self.db.crear_usuario(usr, pwd, nom, self._roles.get(rol))
        if ok:
            messagebox.showinfo("✅", msg, parent=self.win)
            self._limpiar(); self._cargar()
        else:
            messagebox.showerror("❌", msg, parent=self.win)

    def _actualizar(self):
        if not self.seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un usuario.",
                                   parent=self.win); return
        nom    = self.e_nombre.get().strip()
        rol    = self.e_rol.get()
        id_rol = self._roles.get(rol)

        if self.seleccionado == self.usuario_actual['id']:
            if rol != self.usuario_actual['rol']:
                messagebox.showwarning("⚠️", "No puedes cambiar tu propio rol.",
                                       parent=self.win)
                self.e_rol.set(self.usuario_actual['rol']); return

        # Mantener el activo actual del usuario al actualizar
        activo_actual = self.db.obtener_estado_usuario(self.seleccionado, default=1)

        ok, msg = self.db.actualizar_usuario(self.seleccionado, nom, id_rol, activo_actual)
        nueva_pwd = self.e_password.get()
        if ok and nueva_pwd:
            ok_pwd, msg_pwd = self.db.reset_password_admin(self.seleccionado, nueva_pwd)
            if not ok_pwd:
                ok, msg = False, msg_pwd
        if ok:
            messagebox.showinfo("✅", msg, parent=self.win)
            self._limpiar(); self._cargar()
        else:
            messagebox.showerror("❌", msg, parent=self.win)

    def _inhabilitar(self):
        if not self.seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un usuario.",
                                   parent=self.win); return
        if self.seleccionado == self.usuario_actual['id']:
            messagebox.showwarning("⚠️", "No puedes inhabilitarte a ti mismo.",
                                   parent=self.win); return

        nombre = self.e_username.get().strip()
        if not messagebox.askyesno(
                "🚫 Inhabilitar usuario",
                f"¿Inhabilitar a '{nombre}'?\n\n"
                f"El usuario no podrá iniciar sesión hasta que sea habilitado nuevamente.\n"
                f"Todo su historial y movimientos se conservan.",
                parent=self.win): return

        # Confirmación con contraseña del admin
        if not _pedir_password(self.win, self.db, self.usuario_actual['id'],
                               "🔒 Confirmar inhabilitación", self.C):
            return

        ok, msg = self.db.actualizar_usuario(self.seleccionado,
                                              self.e_nombre.get().strip(),
                                              self._roles.get(self.e_rol.get()),
                                              activo=0)
        if ok:
            self.db.registrar_log(self.usuario_actual['id'],
                                   self.usuario_actual['username'],
                                   'Inhabilitar usuario',
                                   f'Usuario: {nombre}')
            messagebox.showinfo("✅",
                                f"Usuario '{nombre}' inhabilitado.\n"
                                f"Ya no podrá iniciar sesión.",
                                parent=self.win)
            self._limpiar(); self._cargar()
        else:
            messagebox.showerror("❌", msg, parent=self.win)

    def _habilitar(self):
        if not self.seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un usuario.",
                                   parent=self.win); return

        nombre = self.e_username.get().strip()
        if not messagebox.askyesno(
                "✅ Habilitar usuario",
                f"¿Habilitar a '{nombre}'?\n\n"
                f"El usuario podrá iniciar sesión nuevamente.",
                parent=self.win): return

        ok, msg = self.db.actualizar_usuario(self.seleccionado,
                                              self.e_nombre.get().strip(),
                                              self._roles.get(self.e_rol.get()),
                                              activo=1)
        if ok:
            self.db.registrar_log(self.usuario_actual['id'],
                                   self.usuario_actual['username'],
                                   'Habilitar usuario',
                                   f'Usuario: {nombre}')
            messagebox.showinfo("✅",
                                f"Usuario '{nombre}' habilitado.\n"
                                f"Ya puede iniciar sesión.",
                                parent=self.win)
            self._limpiar(); self._cargar()
        else:
            messagebox.showerror("❌", msg, parent=self.win)

    def _resetear_password_admin(self):
        if not self.seleccionado:
            messagebox.showwarning("⚠️", "Seleccione un usuario.", parent=self.win); return
        if self.seleccionado == self.usuario_actual['id']:
            messagebox.showwarning("⚠️", "Para cambiar tu propia contraseña usa 'Mi Cuenta'.",
                                   parent=self.win); return

        username = self.e_username.get().strip()
        nueva    = messagebox.askstring if hasattr(messagebox, 'askstring') else None

        # Usar simpledialog
        import tkinter.simpledialog as sd
        nueva_pwd = sd.askstring(
            "🔑 Resetear Contraseña",
            f"Nueva contraseña para '{username}':\n(mínimo 4 caracteres)",
            parent=self.win, show='*')
        if not nueva_pwd:
            return
        if len(nueva_pwd) < 4:
            messagebox.showwarning("⚠️", "La contraseña debe tener al menos 4 caracteres.",
                                   parent=self.win); return

        if not _pedir_password(self.win, self.db, self.usuario_actual['id'],
                               "🔒 Confirmar reset de contraseña", self.C):
            return

        ok, msg = self.db.reset_password_admin(self.seleccionado, nueva_pwd)
        if ok:
            self.db.registrar_log(self.usuario_actual['id'],
                                   self.usuario_actual['username'],
                                   'Reset contraseña admin',
                                   f'Usuario: {username}')
            messagebox.showinfo("✅", f"Contraseña de '{username}' reseteada correctamente.",
                                parent=self.win)
        else:
            messagebox.showerror("❌", msg, parent=self.win)

    def _limpiar(self):
        for attr in ('e_username', 'e_password', 'e_nombre'):
            getattr(self, attr).delete(0, tk.END)
        self.e_rol.set(list(self._roles.keys())[0] if self._roles else '')
        self.seleccionado = None
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())



    def _reporte_actividad(self):
        _abrir_reporte_actividad(self.win, self.db, self.C)

class RolesWindow:
    """Gestión de permisos por rol — con contraseña para eliminar rol."""

    def __init__(self, master, db, usuario_actual=None, C=None):
        self.db             = db
        self.usuario_actual = usuario_actual
        self.roles          = db.obtener_roles()
        self._checks        = {}
        self.C              = _theme(C)

        self.win = ventana_fullscreen(master, "🛡 Gestionar Roles y Permisos",
                                       self.C)
        self._build()

    def _build(self):
        C = self.C

        hdr = tk.Frame(self.win, bg=C['header_bg'], height=50)
        hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr, text="🛡  Configurar Permisos por Rol",
                 font=("Segoe UI", 13, "bold"),
                 bg=C['header_bg'], fg='white').pack(side=tk.LEFT, padx=16)
        body = tk.Frame(self.win, bg=C['bg'])
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8,12))

        tk.Label(body,
                 text="⚠  El rol Administrador siempre tiene acceso total. "
                      "Edite los demás roles libremente.",
                 font=('Segoe UI', 9), bg=C['bg'], fg=C['warning']).pack(anchor='w', pady=(0,8))

        nb = ttk.Notebook(body)
        nb.pack(fill=tk.BOTH, expand=True)

        for rol in self.roles:
            if rol['nombre'] == 'Administrador':
                frm = ttk.Frame(nb); nb.add(frm, text=f"🛡 {rol['nombre']}")
                ttk.Label(frm, text="El Administrador tiene acceso TOTAL.\nNo se puede restringir.",
                          font=('Segoe UI', 11), background=C['bg'],
                          foreground=C['muted']).pack(pady=60)
                continue
            frm = ttk.Frame(nb); nb.add(frm, text=f"👤 {rol['nombre']}")
            self._construir_tab_rol(frm, rol)

    def _construir_tab_rol(self, parent, rol):
        permisos_activos = set(self.db.obtener_permisos_rol(rol['id']))
        self._checks[rol['id']] = {}

        canvas = tk.Canvas(parent, bg=self.C['bg'], highlightthickness=0)
        sb     = ttk.Scrollbar(parent, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)

        inner = ttk.Frame(canvas)
        canvas.create_window((0,0), window=inner, anchor='nw')

        grupos = {
            'Productos':     ['crear_producto', 'editar_producto', 'inhabilitar_producto'],
            'Movimientos':   ['registrar_movimientos','ver_historial_producto'],
            'Reportes':      ['ver_reportes','ver_graficos','reporte_fechas','analizar_excel'],
            'Exportar':      ['exportar_inventario','exportar_movimientos',
                              'exportar_todo','backup_bd'],
            'Proveedores':   ['ver_proveedores','gestionar_proveedores'],
            'Administración':['gestionar_usuarios','gestionar_roles',
                              'ver_auditoria','configuracion'],
            'Cuenta':        ['cambiar_password'],
        }

        col = 0
        for grupo, perms in grupos.items():
            frm_g = ttk.LabelFrame(inner, text=grupo, padding=8)
            frm_g.grid(row=0, column=col, padx=8, pady=8, sticky='n')
            col += 1
            for p in perms:
                var = tk.BooleanVar(value=p in permisos_activos)
                ttk.Checkbutton(frm_g, text=p, variable=var).pack(anchor='w', pady=2)
                self._checks[rol['id']][p] = var

        inner.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))

        btn_frm = ttk.Frame(parent)
        btn_frm.pack(fill=tk.X, padx=12, pady=8)

        ttk.Button(btn_frm, text=f"💾 Guardar permisos de '{rol['nombre']}'",
                   command=lambda r=rol: self._guardar(r)).pack(side=tk.LEFT)

        # Eliminar rol — solo si no es un rol del sistema y hay admin logueado
        if self.usuario_actual and rol['nombre'] not in ('Administrador','Gerente','Empleado'):
            ttk.Button(btn_frm, text=f"🗑️ Eliminar rol '{rol['nombre']}'",
                       command=lambda r=rol: self._eliminar_rol(r),
                       style='Delete.TButton').pack(side=tk.LEFT, padx=8)

    def _guardar(self, rol):
        checks = self._checks.get(rol['id'], {})
        lista  = [p for p, var in checks.items() if var.get()]
        ok, msg = self.db.actualizar_permisos_rol(rol['id'], lista)
        if ok:
            messagebox.showinfo("✅",
                                f"Permisos de '{rol['nombre']}' actualizados.\n"
                                "Los cambios aplican en el próximo login.",
                                parent=self.win)
        else:
            messagebox.showerror("❌", msg, parent=self.win)

    def _eliminar_rol(self, rol):
        """Elimina un rol personalizado con doble confirmación + contraseña."""
        if not messagebox.askyesno("🗑️ Eliminar rol",
                                   f"¿Eliminar el rol '{rol['nombre']}'?\n\n"
                                   f"Todos los usuarios con este rol quedarán sin rol asignado.",
                                   parent=self.win): return

        if not _pedir_password(self.win, self.db, self.usuario_actual['id'],
                               "🔒 Confirmar eliminación de rol", self.C):
            return

        ok, msg = self.db.eliminar_rol(rol['id'])
        if ok:
            messagebox.showinfo("✅", f"Rol '{rol['nombre']}' eliminado.",
                                parent=self.win)
            self.win.destroy()
        else:
            messagebox.showerror("❌", msg, parent=self.win)
