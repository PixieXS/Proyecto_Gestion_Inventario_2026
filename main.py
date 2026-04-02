# ── Instalar dependencias automáticamente si faltan ───────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instalador_deps import instalar_dependencias
if not instalar_dependencias():
    sys.exit(1)

import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from database import DatabaseManager
from gui.ui_helpers import configurar_ventana

MAX_INTENTOS = 5
BLOQUEO_MIN  = 10

IX = {
    # Panel izquierdo — blanco, letras oscuras
    'left_bg':    '#FFFFFF',
    'left_mid':   '#F0F6FF',
    'accent':     '#00B4BC',   # cyan del logo
    'accent2':    '#1A6FD4',   # azul eléctrico del logo
    'left_text':  '#0F172A',   # negro para títulos
    'left_muted': '#0F172A',  
    'left_sub':   '#0F172A',  
    # Panel derecho
    'bg_dark':    '#060E1A',   # casi negro azulado
    'bg_card':    '#0D1F3C',
    'bg_field':   '#0D1F3C',
    'text':       '#E2F0FF',
    'muted':      '#7BA7CC',
    'border_dim': '#1A3A5C',
    'border_on':  '#00C4CC',
    'danger':     '#FF4D6A',
    'warning':    '#F59E0B',
}


def _registrar_intento(db, username, exitoso):
    try:
        db.cursor.execute(
            "INSERT INTO intentos_login (username, exitoso) VALUES (%s, %s)",
            (username, 1 if exitoso else 0))
        db.connection.commit()
    except Exception:
        pass


def _verificar_bloqueo(db, username):
    try:
        limite = datetime.now() - timedelta(minutes=BLOQUEO_MIN)
        db.cursor.execute("""
            SELECT COUNT(*) AS n FROM intentos_login
            WHERE username=%s AND exitoso=0 AND fecha >= %s
        """, (username, limite))
        n = db.cursor.fetchone()['n']
        if n >= MAX_INTENTOS:
            db.cursor.execute("""
                SELECT fecha FROM intentos_login
                WHERE username=%s AND exitoso=0
                ORDER BY fecha DESC LIMIT 1
            """, (username,))
            row = db.cursor.fetchone()
            if row:
                vence    = row['fecha'] + timedelta(minutes=BLOQUEO_MIN)
                restante = (vence - datetime.now()).total_seconds()
                if restante > 0:
                    return True, int(restante)
        return False, 0
    except Exception:
        return False, 0


def _intentos_restantes(db, username):
    try:
        limite = datetime.now() - timedelta(minutes=BLOQUEO_MIN)
        db.cursor.execute("""
            SELECT COUNT(*) AS n FROM intentos_login
            WHERE username=%s AND exitoso=0 AND fecha >= %s
        """, (username, limite))
        n = db.cursor.fetchone()['n']
        return max(0, MAX_INTENTOS - n)
    except Exception:
        return MAX_INTENTOS


def mostrar_login(root, db):
    resultado = [None]

    dialog = tk.Toplevel(root)
    dialog.title("Inventoryx — Iniciar Sesión")
    dialog.grab_set()
    dialog.configure(bg=IX['bg_dark'])
    configurar_ventana(
        dialog,
        width=920,
        height=560,
        min_width=920,
        min_height=560,
        resizable=(False, False),
    )
    dialog.update()

    # ═══════════════════════════════════════════════════════
    # CARGAR LOGO
    # ═══════════════════════════════════════════════════════
    photo_logo = None
    base_dir   = os.path.dirname(os.path.abspath(__file__))

    # Intentar logo_icono.png primero (solo ícono), luego logo.png
    for nombre_logo in ('logo_icono.png', 'logo.png'):
        ruta = os.path.join(base_dir, nombre_logo)
        if os.path.exists(ruta):
            try:
                from PIL import Image, ImageTk
                import numpy as np
                img = Image.open(ruta).convert('RGBA')

                if nombre_logo == 'logo.png':
                    # Recortar solo el ícono
                    arr = np.array(img)
                    mask = np.any(arr[:,:,:3] > 25, axis=2)
                    rows = np.where(mask.any(axis=1))[0]
                    cols = np.where(mask.any(axis=0))[0]
                    if len(rows) and len(cols):
                        p = 15
                        img = img.crop((cols[0]-p, rows[0]-p,
                                        cols[-1]+p, rows[-1]+p))
                    arr = np.array(img)
                    mask_neg = np.all(arr[:,:,:3] < 22, axis=2)
                    arr[mask_neg, 3] = 0
                    img = Image.fromarray(arr)

                # Hacer cuadrado y redimensionar
                s = max(img.size)
                cuad = Image.new('RGBA', (s, s), (0,0,0,0))
                cuad.paste(img, ((s-img.width)//2, (s-img.height)//2))
                cuad = cuad.resize((120, 120), Image.LANCZOS)

                # Componer sobre fondo del panel izquierdo
                bg = Image.new('RGBA', (120, 120), (255, 255, 255, 255))
                bg.paste(cuad, (0,0), cuad)
                photo_logo = ImageTk.PhotoImage(bg)
                break
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════
    # PANEL IZQUIERDO — todo en Canvas
    # ═══════════════════════════════════════════════════════
    cvs = tk.Canvas(dialog, width=390, highlightthickness=0,
                    bg='#FFFFFF')
    cvs.pack(side=tk.LEFT, fill=tk.BOTH)

    # Label para el logo (hijo del canvas para no crear ventana "token")
    lbl_logo = None
    if photo_logo:
        lbl_logo = tk.Label(cvs, image=photo_logo,
                            bg='#FFFFFF', bd=0)
        lbl_logo.image = photo_logo

    def _draw(event=None):
        cvs.delete('bg', 'deco', 'txt')
        cw = cvs.winfo_width()  or 390
        ch = cvs.winfo_height() or 560

        # ── Fondo blanco puro ─────────────────────────────────────────────
        cvs.create_rectangle(0, 0, cw, ch,
                             fill='#FFFFFF', outline='', tags='bg')

        # ── Círculo decorativo tenue ──────────────────────────────────────
        cx, cy2 = cw//2, ch//2 - 20
        for r, col in [(200,'#E8F4FF'),(170,'#D4ECFF'),(140,'#C0E0F8')]:
            cvs.create_oval(cx-r, cy2-r, cx+r, cy2+r,
                            fill='', outline=col,
                            width=1, tags='deco')

        # ── Cuadrícula tecnológica muy tenue ──────────────────────────────
        step = 40
        for x in range(0, cw+step, step):
            cvs.create_line(x, 0, x, ch,
                            fill='#D8EAF6', width=1, tags='deco')
        for y in range(0, ch+step, step):
            cvs.create_line(0, y, cw, y,
                            fill='#D8EAF6', width=1, tags='deco')

        # ── Acento diagonal arriba-derecha ────────────────────────────────
        cvs.create_line(cw-120, 0, cw+20, 160,
                        fill='#B8E8EC', width=2, tags='deco')
        cvs.create_line(cw-80,  0, cw+20, 120,
                        fill='#C8D8F0', width=1, tags='deco')

        # ── Acento diagonal abajo-izquierda ───────────────────────────────
        cvs.create_line(-20, ch-120, 140, ch+20,
                        fill='#C8D8F0', width=2, tags='deco')
        cvs.create_line(-20, ch-80,  100, ch+20,
                        fill='#B8E8EC', width=1, tags='deco')

        # ── Línea divisoria derecha con degradado ────────────────────────────
        cvs.create_rectangle(cw-2, 0, cw, ch,
                             fill='#D0E8F8', outline='', tags='deco')

        # ── LOGO ──────────────────────────────────────────────────────────────
        logo_y = cy2 - 40
        if lbl_logo:
            cvs.delete('logo_win')
            cvs.create_window(cw//2, logo_y,
                              window=lbl_logo,
                              anchor='center',
                              tags='logo_win')
        else:
            cvs.create_text(cw//2, logo_y,
                            text="◈",
                            font=("Segoe UI", 48),
                            fill=IX['accent'],
                            anchor='center', tags='txt')

        # ── NOMBRE "Inventoryx" pegado ────────────────────────────────────────
        nombre_y = cy2 + 15

        # Calcular posición exacta para pegar "Inventory" + "x"
        # Usar fuente fija y calcular offset manual
        fuente_bold = ("Segoe UI", 25, "bold")
        # Crear label temporal para medir
        tmp = tk.Label(dialog, text="Inventory", font=fuente_bold)
        tmp.update_idletasks()
        w_inv = tmp.winfo_reqwidth()
        tmp.destroy()

        start_x = cw//2 - w_inv//2

        cvs.create_text(start_x, nombre_y,
                        text="Inventory",
                        font=fuente_bold,
                        fill=IX['left_text'],
                        anchor='nw', tags='txt')
        cvs.create_text(start_x + w_inv, nombre_y,
                        text="x",
                        font=fuente_bold,
                        fill=IX['accent'],
                        anchor='nw', tags='txt')
        lw = 150
        ly = nombre_y + 40
        cvs.create_rectangle(cw//2 - lw//2, ly,
                             cw//2 + lw//2, ly + 2,
                             fill=IX['accent'], outline='', tags='txt')

        # ── Eslogan ───────────────────────────────────────────────────────────
        cvs.create_text(cw//2, ly + 16,
                        text="Sistema de Gestión de Inventario",
                        font=("Segoe UI", 12),
                        fill=IX['left_sub'],
                        anchor='center', tags='txt')

        # Nombre empresa
        ne = db.get_empresa_nombre()
        offset_feat = 0
        if ne and ne != 'Mi Empresa':
            cvs.create_text(cw//2, ly + 34,
                            text=ne,
                            font=("Segoe UI", 14, "bold"),
                            fill=IX['accent'],
                            anchor='center', tags='txt')
            offset_feat = 18

        # ── Features ─────────────────────────────────────────────────────────
        fy = ly + 55 + offset_feat
        for txt in [
            "Control de inventario en tiempo real",
            "Roles y permisos por usuario",
            "Reportes y estadísticas detallados",
            "Auditoría y trazabilidad completa",
        ]:
            cvs.create_text(cw//2 - 85, fy,
                            text="›",
                            font=("Segoe UI", 12, "bold"),
                            fill=IX['accent'],
                            anchor='w', tags='txt')
            cvs.create_text(cw//2 - 70, fy,
                            text=txt,
                            font=("Segoe UI", 8),
                            fill=IX['left_muted'],
                            anchor='w', tags='txt')
            fy += 19

        # ── Versión ───────────────────────────────────────────────────────────
        cvs.create_text(cw//2, ch - 18,
                        text="v3.0  •  © 2026",
                        font=("Segoe UI", 7),
                        fill=IX['left_sub'],
                        anchor='center', tags='txt')

    cvs.bind('<Configure>', _draw)
    dialog.after(80, _draw)

    # ═══════════════════════════════════════════════════════
    # PANEL DERECHO
    # ═══════════════════════════════════════════════════════
    right = tk.Frame(dialog, bg=IX['bg_dark'])
    right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    form = tk.Frame(right, bg=IX['bg_dark'])
    form.place(relx=0.5, rely=0.5, anchor='center')

    tk.Label(form, text="Iniciar Sesión",
             font=("Segoe UI", 22, "bold"),
             bg=IX['bg_dark'], fg=IX['text']).pack(anchor='w')

    tk.Label(form, text="Accede con tus credenciales asignadas",
             font=("Segoe UI", 9),
             bg=IX['bg_dark'], fg=IX['muted']).pack(anchor='w', pady=(3, 26))

    def _campo(label, show=None):
        tk.Label(form, text=label,
                 font=("Segoe UI", 8, "bold"),
                 bg=IX['bg_dark'], fg=IX['muted'],
                 anchor='w').pack(fill=tk.X, pady=(0, 4))
        frm_b = tk.Frame(form, bg=IX['border_dim'], pady=1, padx=1)
        frm_b.pack(fill=tk.X, pady=(0, 16))
        frm_i = tk.Frame(frm_b, bg=IX['bg_field'])
        frm_i.pack(fill=tk.X)
        e = tk.Entry(frm_i,
                     font=("Segoe UI", 11),
                     bg=IX['bg_field'], fg=IX['text'],
                     insertbackground=IX['accent'],
                     relief='flat', bd=10,
                     show=show or '', width=26)
        e.pack(fill=tk.X)
        e.bind('<FocusIn>',  lambda ev: frm_b.config(bg=IX['border_on']))
        e.bind('<FocusOut>', lambda ev: frm_b.config(bg=IX['border_dim']))
        return e

    e_user = _campo("USUARIO")
    e_pass = _campo("CONTRASEÑA", show='*')
    e_user.focus()

    msg = tk.Label(form, text='',
                   font=("Segoe UI", 8),
                   bg=IX['bg_dark'], fg=IX['danger'],
                   wraplength=280, justify='left')
    msg.pack(anchor='w', pady=(0, 2))

    lbl_intentos = tk.Label(form, text='',
                             font=("Segoe UI", 7),
                             bg=IX['bg_dark'], fg=IX['warning'])
    lbl_intentos.pack(anchor='w', pady=(0, 10))

    # Botón con color cyan del logo
    btn = tk.Button(form,
                    text="Ingresar  →",
                    font=("Segoe UI", 11, "bold"),
                    bg=IX['accent2'], fg='white',
                    relief='flat', cursor='hand2',
                    padx=24, pady=11,
                    activebackground='#1558A8',
                    activeforeground='white')
    btn.pack(fill=tk.X)
    btn.bind('<Enter>', lambda e: btn.config(bg='#1558A8'))
    btn.bind('<Leave>', lambda e: btn.config(bg=IX['accent2']))

 
    def _shake(count=0, direction=1):
        if count >= 8:
            form.place(relx=0.5, rely=0.5, anchor='center'); return
        form.place(relx=0.5, rely=0.5, anchor='center', x=direction*6)
        dialog.after(35, lambda: _shake(count+1, -direction))

    def _login(event=None):
        username = e_user.get().strip()
        password = e_pass.get()
        if not username or not password:
            msg.config(text="Ingrese usuario y contraseña.")
            return
        bloqueado, restante = _verificar_bloqueo(db, username)
        if bloqueado:
            mins = restante // 60; segs = restante % 60
            msg.config(text=f"Cuenta bloqueada. Intente en {mins}m {segs}s.")
            lbl_intentos.config(text="")
            return
        usuario, error = db.autenticar_usuario(username, password)
        if usuario:
            _registrar_intento(db, username, exitoso=True)
            resultado[0] = usuario
            dialog.destroy()
        else:
            _registrar_intento(db, username, exitoso=False)
            bloqueado2, _ = _verificar_bloqueo(db, username)
            if bloqueado2:
                msg.config(text=f"Cuenta bloqueada por {BLOQUEO_MIN} minutos.")
                lbl_intentos.config(text="")
            else:
                restantes = _intentos_restantes(db, username)
                lbl_intentos.config(
                    text=f"  {restantes} intento(s) restantes antes del bloqueo")
                msg.config(text="Usuario o contraseña incorrectos.")
            e_pass.delete(0, tk.END)
            _shake()

    btn.config(command=_login)
    dialog.bind('<Return>', _login)

    root.wait_window(dialog)
    return resultado[0]


def main():
    root = tk.Tk()
    root.withdraw()
    try:
        root.iconbitmap('app_icon.ico')
    except Exception:
        pass

    from configurador import es_primera_instalacion, mostrar_configurador

    # Mostrar configurador si es primera instalación
    if es_primera_instalacion():
        ok = mostrar_configurador(root, motivo='primera_instalacion')
        if not ok:
            root.destroy(); return

    # Intentar conectar — si falla o BD no existe, abrir configurador
    def _bd_existe(cfg):
        """Verifica si la base de datos existe en MySQL."""
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=cfg['host'], port=int(cfg.get('port', 3306)),
                user=cfg['user'], password=cfg['password'],
                connection_timeout=5)
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES LIKE %s", (cfg['database'],))
            existe = cursor.fetchone() is not None
            cursor.close(); conn.close()
            return existe
        except Exception:
            return False

    import config as _cfg_mod
    import importlib
    import database.conexion as _conexion_mod

    def _recargar_config():
        """Recarga config y sincroniza DB_CONFIG en todos los módulos."""
        importlib.reload(_cfg_mod)
        # Sincronizar el DB_CONFIG que conexion.py importó directamente
        _conexion_mod.DB_CONFIG.update(_cfg_mod.DB_CONFIG)

    intentos = 0
    while True:
        # Verificar si la BD existe antes de conectar
        if not _bd_existe(_cfg_mod.DB_CONFIG):
            ok = mostrar_configurador(root, motivo='primera_instalacion')
            if not ok:
                root.destroy(); return
            _recargar_config()
            continue

        db = DatabaseManager()
        if db.connect():
            break

        intentos += 1
        if intentos >= 3:
            messagebox.showerror("Error",
                                 "No se pudo conectar tras 3 intentos.\n"
                                 "Verifique que MySQL esté corriendo.")
            root.destroy(); return
        ok = mostrar_configurador(root, motivo='fallo_conexion')
        if not ok:
            root.destroy(); return
        _recargar_config()

    if not db.create_tables():
        messagebox.showerror("Error", "Error al inicializar las tablas.")
        root.destroy(); return

    usuario = mostrar_login(root, db)
    if not usuario:
        db.disconnect(); root.destroy(); return

    root.deiconify()
    from gui.app import InventoryManagementApp
    app = InventoryManagementApp(root, db, usuario)
    root.protocol("WM_DELETE_WINDOW", app.cerrar)
    root.mainloop()


if __name__ == "__main__":
    main()
