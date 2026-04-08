import tkinter as tk
import os


def construir_topbar(root, titulo_var, C, app):
    bar = tk.Frame(root, bg=C['header_bg'], height=44)
    bar.pack(fill=tk.X)
    bar.pack_propagate(False)

    # Botón colapsar
    app._btn_colapsar = tk.Button(
        bar, text="☰", font=("Segoe UI", 14),
        bg=C['header_bg'], fg='white', relief='flat', cursor='hand2', padx=10,
        activebackground=C['sidebar_bg'], activeforeground='white',
        command=app._toggle_sidebar)
    app._btn_colapsar.pack(side=tk.LEFT, padx=(4, 0))

    tk.Label(bar, textvariable=titulo_var,
             font=("Segoe UI", 11, "bold"),
             bg=C['header_bg'], fg='white').pack(side=tk.LEFT, padx=10)

    # Zona derecha
    right = tk.Frame(bar, bg=C['header_bg'])
    right.pack(side=tk.RIGHT, padx=10)

    # Usuario
    tk.Label(right,
             text=f"👤 {app.usuario['nombre_completo']}  •  🛡️ {app.usuario['rol']}",
             font=("Segoe UI", 8), bg=C['header_bg'], fg=C['muted']
             ).pack(side=tk.LEFT, padx=(0, 14))

    # Botón desplegable de paleta
    from gui.estilos import PALETAS
    paleta_actual = PALETAS.get(C['nombre'], {})
    btn_tema = tk.Button(
        right, text="🎨 Cambiar Tema  ▾",
        font=("Segoe UI", 8, "bold"),
        bg=C['primary'], fg='white',
        relief='flat', cursor='hand2',
        padx=10, pady=4,
        activebackground=C['secondary'], activeforeground='white')
    btn_tema.pack(side=tk.LEFT, padx=4)

    def _abrir_menu_tema(e=None):
        menu = tk.Menu(right, tearoff=0,
                       bg=C['surface'], fg=C['text'],
                       activebackground=C['primary'],
                       activeforeground='white',
                       font=("Segoe UI", 9),
                       relief='flat', bd=0)
        for pal_key, pal in PALETAS.items():
            activo = pal_key == C['nombre']
            label  = f"✔  {pal['label']}" if activo else f"    {pal['label']}"
            menu.add_command(label=label,
                             command=lambda k=pal_key: app._cambiar_paleta(k))
        x = btn_tema.winfo_rootx()
        y = btn_tema.winfo_rooty() + btn_tema.winfo_height()
        menu.tk_popup(x, y)

    btn_tema.config(command=_abrir_menu_tema)

    # Actualizar
    tk.Button(right, text="🔄", font=("Segoe UI", 11),
              bg=C['header_bg'], fg='white', relief='flat',
              cursor='hand2', padx=6,
              activebackground=C['sidebar_bg'], activeforeground='white',
              command=app._refrescar_dashboard
              ).pack(side=tk.LEFT, padx=(6, 0))


def construir_sidebar(container, app, C,
                      empresa_nombre="Mi Empresa", logo_path="",
                      colapsado=False):
    sw = container.winfo_screenwidth()
    sh = container.winfo_screenheight()

    W_EXP = 220 if sw >= 1440 else (195 if sw >= 1280 else 170)
    W_COL = 52
    W     = W_COL if colapsado else W_EXP

    SBG   = C['sidebar_bg']
    ACT   = C['primary']
    HOV   = C['acc_hover']
    FG    = '#CBD5E1'
    MUTED = '#475569'
    fn    = ("Segoe UI", 9 if sw >= 1366 else 8)

    outer = tk.Frame(container, bg=SBG, width=W)
    outer.pack(side=tk.LEFT, fill=tk.Y)
    outer.pack_propagate(False)
    app._sidebar_outer = outer

    cvs = tk.Canvas(outer, bg=SBG, highlightthickness=0, width=W)
    cvs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    inner = tk.Frame(cvs, bg=SBG, width=W)
    win_id = cvs.create_window((0, 0), window=inner, anchor='nw')

    inner.bind('<Configure>', lambda e: cvs.configure(scrollregion=cvs.bbox('all')))
    cvs.bind('<Configure>',   lambda e: cvs.itemconfig(win_id, width=e.width))
    cvs.bind_all('<MouseWheel>',
                 lambda e: cvs.yview_scroll(int(-1*(e.delta/120)), "units"))

    app._sidebar_btns = {}
    app._acc_open     = None   # sección de acordeón actualmente abierta

    # ── Logo ──────────────────────────────────────────────────────────────────
    logo_size  = 42 if colapsado else (54 if sw < 1366 else 66)
    logo_frame = tk.Frame(inner, bg=SBG)
    logo_frame.pack(fill=tk.X, pady=(14, 6))

    logo_ok = False
    if logo_path:
        ruta = logo_path if os.path.isabs(logo_path) else os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', logo_path)
        if os.path.exists(ruta):
            try:
                from PIL import Image, ImageTk
                img   = Image.open(ruta).resize((logo_size, logo_size), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl   = tk.Label(logo_frame, image=photo, bg=SBG)
                lbl.image = photo
                lbl.pack(pady=(0, 3))
                logo_ok = True
            except Exception:
                pass

    if not logo_ok:
        tk.Label(logo_frame, text="📦",
                 font=("Segoe UI", logo_size // 3),
                 bg=SBG, fg='white').pack(pady=(0, 2))

    if not colapsado:
        app._lbl_empresa = tk.Label(
            logo_frame, text=empresa_nombre,
            font=("Segoe UI", 9 if sw < 1366 else 10, "bold"),
            bg=SBG, fg='white', wraplength=W - 16)
        app._lbl_empresa.pack()

    _sep(inner, SBG)

    # ── Acceso directo sin acordeón ───────────────────────────────────────────
    def _direct(icon, label, cmd, key):
        txt  = icon if colapsado else f"  {icon}  {label}"
        btn  = tk.Button(inner, text=txt, font=fn, anchor='center' if colapsado else 'w',
                         bg=SBG, fg=FG,
                         activebackground=HOV, activeforeground='white',
                         relief='flat', bd=0, cursor='hand2',
                         padx=4 if colapsado else 10,
                         pady=7 if sh >= 800 else 5,
                         command=cmd)
        btn.pack(fill=tk.X, padx=2 if colapsado else 4, pady=1)
        if colapsado:
            _tooltip(btn, label, C)

        def _e(e):
            if getattr(app, '_pagina_activa', None) != key:
                btn.config(bg=HOV, fg='white')
        def _l(e):
            btn.config(
                bg=ACT if getattr(app, '_pagina_activa', None) == key else SBG,
                fg='white')
        btn.bind('<Enter>', _e)
        btn.bind('<Leave>', _l)
        app._sidebar_btns[key] = btn
        return btn

    # ── Sección acordeón ──────────────────────────────────────────────────────
    def _accordion(icon, label, items, sec_key):
        """
        items = lista de (icon, label, comando)
        """
        # Frame contenedor
        sec_frame = tk.Frame(inner, bg=SBG)
        sec_frame.pack(fill=tk.X)

        # Header del acordeón
        hdr_frame = tk.Frame(sec_frame, bg=SBG)
        hdr_frame.pack(fill=tk.X)

        arrow_var = tk.StringVar(value="▶")
        is_open   = [False]

        if colapsado:
            # En modo colapsado solo icono con tooltip y submenú flotante
            btn_hdr = tk.Button(hdr_frame, text=icon,
                                font=("Segoe UI", 13),
                                anchor='center', bg=SBG, fg=FG,
                                activebackground=HOV, activeforeground='white',
                                relief='flat', bd=0, cursor='hand2',
                                padx=4, pady=7 if sh >= 800 else 5)
            btn_hdr.pack(fill=tk.X, padx=2, pady=1)
            _tooltip_submenu(btn_hdr, label, items, C)
            return

        btn_hdr = tk.Button(hdr_frame,
                            text=f"  {icon}  {label}",
                            font=fn, anchor='w',
                            bg=SBG, fg=FG,
                            activebackground=HOV, activeforeground='white',
                            relief='flat', bd=0, cursor='hand2',
                            padx=10, pady=7 if sh >= 800 else 5)
        btn_hdr.pack(side=tk.LEFT, fill=tk.X, expand=True)

        lbl_arrow = tk.Label(hdr_frame, textvariable=arrow_var,
                             font=("Segoe UI", 9),
                             bg=SBG, fg=MUTED, padx=8)
        lbl_arrow.pack(side=tk.RIGHT)

        # Frame de items (inicialmente oculto)
        items_frame = tk.Frame(sec_frame, bg=C['acc_open'])
        # NO lo packs todavía

        for item_icon, item_label, item_cmd in items:
            sub = tk.Button(items_frame,
                            text=f"      {item_icon}  {item_label}",
                            font=fn, anchor='w',
                            bg=C['acc_open'], fg=FG,
                            activebackground=ACT, activeforeground='white',
                            relief='flat', bd=0, cursor='hand2',
                            padx=10, pady=5,
                            command=item_cmd)
            sub.pack(fill=tk.X, padx=2, pady=1)
            sub.bind('<Enter>', lambda e, b=sub: b.config(bg=ACT, fg='white'))
            sub.bind('<Leave>', lambda e, b=sub: b.config(bg=C['acc_open'], fg=FG))

        def _toggle(e=None):
            # Auto-colapso: cerrar sección abierta anterior
            prev = getattr(app, '_acc_open', None)
            if prev and prev is not items_frame:
                try:
                    prev.pack_forget()
                    # resetear flecha del prev
                    if hasattr(prev, '_arrow_var'):
                        prev._arrow_var.set("▶")
                except Exception:
                    pass

            if is_open[0]:
                items_frame.pack_forget()
                arrow_var.set("▶")
                btn_hdr.config(bg=SBG)
                is_open[0] = False
                app._acc_open = None
            else:
                items_frame.pack(fill=tk.X)
                arrow_var.set("▼")
                btn_hdr.config(bg=C['acc_open'])
                is_open[0] = True
                app._acc_open = items_frame
                items_frame._arrow_var = arrow_var

        btn_hdr.config(command=_toggle)
        lbl_arrow.bind('<Button-1>', _toggle)
        btn_hdr.bind('<Enter>',
                     lambda e: btn_hdr.config(bg=HOV if not is_open[0] else C['acc_open']))
        btn_hdr.bind('<Leave>',
                     lambda e: btn_hdr.config(bg=C['acc_open'] if is_open[0] else SBG))

    # ── Construir navegación ──────────────────────────────────────────────────
    _sep_lbl(inner, SBG, MUTED, "PRINCIPAL")
    _direct("🏠", "Inicio",         lambda: app._mostrar_pagina('dashboard'),  'dashboard')
    _direct("📦", "Inventario",     lambda: app._mostrar_pagina('inventario'), 'inventario')

    # Botón Cerrar Sesión — visible y claro, bajo los accesos directos
    if colapsado:
        cs_txt = "🚪"
        cs_pad = 4
    else:
        cs_txt = "  🚪  Cerrar Sesión"
        cs_pad = 10

    cs_btn = tk.Button(inner, text=cs_txt,
                       font=fn, anchor='center' if colapsado else 'w',
                       bg=C['danger'], fg='white',
                       activebackground='#DC2626', activeforeground='white',
                       relief='flat', bd=0, cursor='hand2',
                       padx=cs_pad, pady=7 if sh >= 800 else 5,
                       command=app._cerrar_sesion)
    cs_btn.pack(fill=tk.X, padx=4, pady=(2, 6))
    if colapsado:
        _tooltip(cs_btn, "Cerrar Sesión", C)

    _sep(inner, SBG)

    # Inventario (acordeón)
    inv_items = []
    if app.perm('registrar_movimientos') or app.perm('crear_producto') or app.perm('ver_proveedores'):
        if app.perm('registrar_movimientos') or app.perm('crear_producto'):
            inv_items.append(("🔎", "Movimientos",   app.abrir_busqueda_movimientos))
        if app.perm('ver_proveedores'):
            inv_items.append(("🏭", "Proveedores", app.abrir_proveedores))
        if app.perm('crear_producto'):
            inv_items.append(("📥", "Importar Excel", app.abrir_importar_excel))
        if inv_items:
            _sep_lbl(inner, SBG, MUTED, "INVENTARIO")
            _accordion("📋", "Gestión", inv_items, 'inv')

    # Reportes (acordeón)
    rep_items = []
    if (app.perm('ver_reportes') or app.perm('ver_graficos') or
            app.perm('reporte_fechas') or app.perm('analizar_excel')):
        if app.perm('ver_reportes'):
            rep_items.append(("📈", "Centro",      app.abrir_centro_reportes))
            rep_items.append(("📦", "Inventario",  app.gen_reporte_inventario))
            rep_items.append(("🚛", "Movimientos", app.gen_reporte_movimientos))
        if app.perm('reporte_fechas'):
            rep_items.append(("📆", "Por Fechas",  app.reporte_rango_fechas))
        if app.perm('ver_graficos'):
            rep_items.append(("📊", "Gráficos",    app.abrir_graficos))
        if app.perm('analizar_excel'):
            rep_items.append(("🔍", "Analizar Excel", app.abrir_analizador_excel))
        if rep_items:
            _sep_lbl(inner, SBG, MUTED, "REPORTES")
            _accordion("📊", "Reportes", rep_items, 'rep')

    # Administración (acordeón)
    adm_items = []
    if (app.perm('gestionar_usuarios') or app.perm('gestionar_roles') or
            app.perm('configuracion') or app.perm('ver_auditoria') or
            app.perm('backup_bd')):
        if app.perm('gestionar_usuarios'):
            adm_items.append(("👥", "Usuarios",        app.abrir_gestion_usuarios))
        if app.perm('gestionar_roles'):
            adm_items.append(("🛡️",  "Roles",           app.abrir_gestion_roles))
        if app.perm('configuracion'):
            adm_items.append(("🏷️",  "Categorías",      app.abrir_categorias))
            adm_items.append(("⚙️",  "Config. Sistema", app.abrir_config_sistema))
            adm_items.append(("🧩",  "Campos de Producto", app.abrir_campos_opcionales))
        if app.perm('ver_auditoria'):
            adm_items.append(("🧾", "Auditoría",       app.abrir_log_actividad))
        if adm_items:
            _sep_lbl(inner, SBG, MUTED, "ADMINISTRACIÓN")
            _accordion("⚙️", "Administración", adm_items, 'adm')

    # Backups — sección dedicada solo para quien tiene permiso
    if app.perm('backup_bd'):
        _sep_lbl(inner, SBG, MUTED, "BACKUPS")
        _accordion("💾", "Backup y Restauración", [
            ("💾", "Backup y Restauración",  app.abrir_backup),
        ], 'bkp')

    tk.Frame(inner, bg=SBG, height=60).pack()

    # ── Zona inferior fija ────────────────────────────────────────────────────
    bottom = tk.Frame(outer, bg=SBG)
    bottom.pack(fill=tk.X, side=tk.BOTTOM, padx=4, pady=6)
    tk.Frame(outer, bg='#334155', height=1).pack(fill=tk.X, side=tk.BOTTOM)

    if not colapsado:
        tk.Label(bottom, text=f"👤  {app.usuario['nombre_completo']}",
                 font=("Segoe UI", 8, "bold"),
                 bg=SBG, fg='white', anchor='w',
                 wraplength=W - 10).pack(fill=tk.X, pady=(0, 1))
        tk.Label(bottom, text=f"🛡️  {app.usuario['rol']}",
                 font=("Segoe UI", 8), bg=SBG, fg='#94A3B8',
                 anchor='w').pack(fill=tk.X, pady=(0, 5))

    row = tk.Frame(bottom, bg=SBG)
    row.pack(fill=tk.X)
    for txt, cmd, col in [("🔑", app.cambiar_password, C['primary']),
                           ("❓", app._abrir_manual,    '#2D4E6F')]:
        tk.Button(row, text=txt, font=("Segoe UI", 11),
                  bg=col, fg='white', relief='flat', cursor='hand2',
                  padx=4, pady=3,
                  activebackground=SBG, activeforeground='white',
                  command=cmd).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

    return outer


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sep(parent, bg):
    tk.Frame(parent, bg='#334155', height=1).pack(fill=tk.X, padx=10, pady=3)


def _sep_lbl(parent, bg, fg, texto):
    tk.Label(parent, text=texto,
             font=("Segoe UI", 7, "bold"),
             bg=bg, fg=fg, anchor='w'
             ).pack(fill=tk.X, padx=12, pady=(8, 1))


def _tooltip(widget, text, C):
    tip = None
    def show(e):
        nonlocal tip
        x = widget.winfo_rootx() + widget.winfo_width() + 4
        y = widget.winfo_rooty() + 4
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tk.Label(tip, text=text, bg='#1E293B', fg='white',
                 font=("Segoe UI", 9), padx=8, pady=4).pack()
    def hide(e):
        nonlocal tip
        if tip:
            tip.destroy(); tip = None
    widget.bind('<Enter>', show)
    widget.bind('<Leave>', hide)


def _tooltip_submenu(widget, titulo, items, C):
    """Submenú flotante para modo colapsado."""
    popup = None

    def show(e):
        nonlocal popup
        x = widget.winfo_rootx() + widget.winfo_width() + 2
        y = widget.winfo_rooty()
        popup = tk.Toplevel(widget)
        popup.wm_overrideredirect(True)
        popup.wm_geometry(f"+{x}+{y}")
        popup.configure(bg='#1E293B')

        tk.Label(popup, text=titulo,
                 bg='#334155', fg='white',
                 font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, anchor='w'
                 ).pack(fill=tk.X)

        for icon, label, cmd in items:
            def _click(c=cmd):
                popup.destroy()
                c()
            b = tk.Button(popup,
                          text=f"  {icon}  {label}",
                          font=("Segoe UI", 9), anchor='w',
                          bg='#1E293B', fg='#CBD5E1',
                          activebackground=C['primary'], activeforeground='white',
                          relief='flat', bd=0, cursor='hand2',
                          padx=12, pady=5,
                          command=_click)
            b.pack(fill=tk.X)
            b.bind('<Enter>', lambda ev, btn=b: btn.config(bg=C['primary'], fg='white'))
            b.bind('<Leave>', lambda ev, btn=b: btn.config(bg='#1E293B', fg='#CBD5E1'))

        popup.bind('<Leave>', lambda e: popup.destroy() if popup.winfo_exists() else None)

    def hide(e):
        pass  # se destruye solo al salir

    widget.bind('<Enter>', show)
