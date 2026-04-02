import tkinter as tk
from tkinter import ttk


WINDOW_SIZE_PRESETS = {
    "main": {"width": 0.94, "height": 0.90, "min_width": 1200, "min_height": 760},
    "xl": {"width": 0.90, "height": 0.86, "min_width": 1120, "min_height": 700},
    "large": {"width": 1180, "height": 760, "min_width": 980, "min_height": 620},
    "medium": {"width": 860, "height": 620, "min_width": 720, "min_height": 500},
    "small": {"width": 560, "height": 360, "min_width": 420, "min_height": 280},
    "dialog": {"width": 420, "height": 260, "min_width": 360, "min_height": 220},
}


def _screen_size(win):
    return max(int(win.winfo_screenwidth() or 0), 1024), max(int(win.winfo_screenheight() or 0), 768)


def _resolve_dimension(value, screen_value, fallback):
    if value is None:
        value = fallback
    if isinstance(value, float) and 0 < value <= 1:
        return int(screen_value * value)
    return int(value)


def centrar_ventana(win, width, height):
    screen_w, screen_h = _screen_size(win)
    width = min(max(int(width), 320), screen_w)
    height = min(max(int(height), 220), screen_h)
    x = max((screen_w - width) // 2, 0)
    y = max((screen_h - height) // 2, 0)
    win.geometry(f"{width}x{height}+{x}+{y}")


def configurar_ventana(
        win, *,
        size="medium",
        width=None,
        height=None,
        min_width=None,
        min_height=None,
        pad_x=32,
        pad_y=72,
        center=True,
        resizable=None,
        start_maximized=False):
    """
    Configura tamanio inicial, minimo y centrado para cualquier ventana Tk/Toplevel.

    `size` puede ser: main, xl, large, medium, small o dialog.
    """
    preset = WINDOW_SIZE_PRESETS.get(size, WINDOW_SIZE_PRESETS["medium"])
    screen_w, screen_h = _screen_size(win)
    available_w = max(screen_w - pad_x, 360)
    available_h = max(screen_h - pad_y, 240)

    target_w = min(max(_resolve_dimension(width, screen_w, preset["width"]), 320), available_w)
    target_h = min(max(_resolve_dimension(height, screen_h, preset["height"]), 240), available_h)

    resolved_min_w = min(max(_resolve_dimension(min_width, screen_w, preset["min_width"]), 320), target_w)
    resolved_min_h = min(max(_resolve_dimension(min_height, screen_h, preset["min_height"]), 220), target_h)

    if resizable is not None:
        win.resizable(*resizable)
    try:
        win.minsize(resolved_min_w, resolved_min_h)
    except Exception:
        pass

    if start_maximized:
        try:
            win.state("zoomed")
            return {
                "width": target_w,
                "height": target_h,
                "min_width": resolved_min_w,
                "min_height": resolved_min_h,
            }
        except Exception:
            pass

    if center:
        centrar_ventana(win, target_w, target_h)
    else:
        win.geometry(f"{target_w}x{target_h}")

    return {
        "width": target_w,
        "height": target_h,
        "min_width": resolved_min_w,
        "min_height": resolved_min_h,
    }


def ajustar_ventana_a_contenido(
        win, *,
        extra_width=24,
        extra_height=24,
        pad_x=32,
        pad_y=72,
        center=True):
    """
    Agranda la ventana si el contenido inicial requiere mas espacio, sin salir de la pantalla.
    """
    try:
        win.update_idletasks()
    except Exception:
        return

    screen_w, screen_h = _screen_size(win)
    available_w = max(screen_w - pad_x, 360)
    available_h = max(screen_h - pad_y, 240)

    current_w = max(int(win.winfo_width() or 0), 1)
    current_h = max(int(win.winfo_height() or 0), 1)
    requested_w = min(max(int(win.winfo_reqwidth() or 0) + extra_width, current_w), available_w)
    requested_h = min(max(int(win.winfo_reqheight() or 0) + extra_height, current_h), available_h)

    if requested_w == current_w and requested_h == current_h:
        return
    if center:
        centrar_ventana(win, requested_w, requested_h)
    else:
        win.geometry(f"{requested_w}x{requested_h}")


def bloquear_columnas(tree):
    """Impide mover o redimensionar encabezados del Treeview."""
    tree.bind(
        "<Button-1>",
        lambda e: "break" if tree.identify_region(e.x, e.y) == "separator" else None)
    tree.bind(
        "<ButtonRelease-1>",
        lambda e: "break" if tree.identify_region(e.x, e.y) == "separator" else None)
    tree.bind(
        "<B1-Motion>",
        lambda e: "break" if tree.identify_region(e.x, e.y) == "separator" else None)


def pedir_confirmacion_password(
        master, db, id_usuario, titulo, mensaje, *,
        bg="#F1F5F9", title_fg="#1E293B", prompt_text="Contrasena:",
        button_style="Delete.TButton", confirm_text="Confirmar",
        cancel_text="Cancelar", geometry="360x200", wraplength=320):
    """Dialogo reutilizable para confirmar acciones con la contrasena actual."""
    resultado = [False]

    win = tk.Toplevel(master)
    win.title(titulo)
    win.configure(bg=bg)
    win.grab_set()

    width_txt, height_txt = str(geometry).lower().split("x", 1)
    configurar_ventana(
        win,
        width=int(width_txt),
        height=int(height_txt),
        min_width=int(width_txt),
        min_height=int(height_txt),
        resizable=(False, False),
    )

    tk.Label(
        win,
        text="Confirmacion de seguridad",
        font=("Segoe UI", 11, "bold"),
        bg=bg,
        fg=title_fg).pack(pady=(18, 4))
    tk.Label(
        win,
        text=mensaje,
        font=("Segoe UI", 9),
        bg=bg,
        fg="#64748B",
        wraplength=wraplength,
        justify="center").pack(pady=(0, 12))

    frm = ttk.Frame(win)
    frm.pack()
    ttk.Label(frm, text=prompt_text).grid(row=0, column=0, padx=8, pady=6, sticky="e")
    e_pwd = ttk.Entry(frm, width=22, show="*")
    e_pwd.grid(row=0, column=1, pady=6)
    e_pwd.focus()

    lbl_err = tk.Label(win, text="", font=("Segoe UI", 9), bg=bg, fg="#EF4444")
    lbl_err.pack()

    def confirmar(event=None):
        pwd = e_pwd.get()
        if not pwd:
            lbl_err.config(text="Ingrese su contrasena.")
            return
        try:
            if db.verificar_password_usuario(id_usuario, pwd):
                resultado[0] = True
                win.destroy()
            else:
                lbl_err.config(text="Contrasena incorrecta.")
                e_pwd.delete(0, tk.END)
                e_pwd.focus()
        except Exception as e:
            lbl_err.config(text=str(e))

    win.bind("<Return>", confirmar)
    frm_b = ttk.Frame(win)
    frm_b.pack(pady=10)
    ttk.Button(
        frm_b,
        text=confirm_text,
        command=confirmar,
        style=button_style).pack(side=tk.LEFT, padx=6)
    ttk.Button(
        frm_b,
        text=cancel_text,
        command=win.destroy,
        style="Neutral.TButton").pack(side=tk.LEFT, padx=6)

    master.wait_window(win)
    return resultado[0]
