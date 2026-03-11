"""
Sistema de Gestión de Inventario v3.0
"""

import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager


def mostrar_login(root, db):
    """Ventana de login con autenticación desde la BD."""
    resultado = [None]

    dialog = tk.Toplevel(root)
    dialog.title("🔐 Iniciar Sesión")
    dialog.geometry("380x290")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.configure(bg="#F8FAFC")
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - 190
    y = (dialog.winfo_screenheight() // 2) - 145
    dialog.geometry(f"380x290+{x}+{y}")

    tk.Label(dialog, text="📦 Inventario STS", font=("Segoe UI", 15, "bold"),
             bg="#F8FAFC", fg="#2563EB").pack(pady=(22, 4))
    tk.Label(dialog, text="Ingrese sus credenciales", font=("Segoe UI", 9),
             bg="#F8FAFC", fg="#64748B").pack(pady=(0, 14))

    frm = tk.Frame(dialog, bg="#F8FAFC")
    frm.pack()

    tk.Label(frm, text="Usuario:", font=("Segoe UI", 10), bg="#F8FAFC").grid(
        row=0, column=0, sticky="e", padx=10, pady=7)
    e_user = ttk.Entry(frm, width=22, font=("Segoe UI", 10))
    e_user.grid(row=0, column=1, pady=7)
    e_user.focus()

    tk.Label(frm, text="Contraseña:", font=("Segoe UI", 10), bg="#F8FAFC").grid(
        row=1, column=0, sticky="e", padx=10, pady=7)
    e_pass = ttk.Entry(frm, width=22, show="*", font=("Segoe UI", 10))
    e_pass.grid(row=1, column=1, pady=7)

    msg = tk.Label(dialog, text="", font=("Segoe UI", 9), bg="#F8FAFC", fg="#EF4444")
    msg.pack(pady=(6, 0))

    def login(event=None):
        usuario, error = db.autenticar_usuario(e_user.get().strip(), e_pass.get())
        if usuario:
            resultado[0] = usuario
            dialog.destroy()
        else:
            msg.config(text=f"❌ {error}")
            e_pass.delete(0, tk.END)

    dialog.bind("<Return>", login)

    btn_frame = tk.Frame(dialog, bg="#F8FAFC")
    btn_frame.pack(pady=12)
    ttk.Button(btn_frame, text="  Ingresar  ", command=login).pack()

    tk.Label(dialog, text="Por defecto: admin / admin123",
             font=("Segoe UI", 8), bg="#F8FAFC", fg="#94A3B8").pack(pady=(0, 6))

    root.wait_window(dialog)
    return resultado[0]


def main():
    root = tk.Tk()
    root.withdraw()

    try:
        root.iconbitmap('app_icon.ico')
    except Exception:
        pass

    db = DatabaseManager()
    if not db.connect():
        messagebox.showerror("Error", "No se pudo conectar a la base de datos.\n"
                             "Verifique config.py y que MySQL esté corriendo.")
        root.destroy()
        return

    if not db.create_tables():
        messagebox.showerror("Error", "Error al inicializar las tablas.")
        root.destroy()
        return

    usuario = mostrar_login(root, db)
    if not usuario:
        db.disconnect()
        root.destroy()
        return

    root.deiconify()
    # Importar aquí para evitar import circular
    from gui import InventoryManagementApp
    app = InventoryManagementApp(root, db, usuario)
    root.protocol("WM_DELETE_WINDOW", app.cerrar)
    root.mainloop()


if __name__ == "__main__":
    main()

