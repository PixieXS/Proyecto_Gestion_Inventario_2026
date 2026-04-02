"""
Ventana de backup y restauracion.

La UI solo coordina confirmaciones y mensajes. El trabajo de archivos vive en
`backup_storage.py` y la ejecucion SQL en la capa `database`.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gui.ui_helpers import bloquear_columnas, configurar_ventana, pedir_confirmacion_password
from modulos.backup_storage import BackupStorage, MAX_BACKUPS


def _pedir_password(master, db, id_usuario, titulo, mensaje):
    return pedir_confirmacion_password(
        master,
        db,
        id_usuario,
        titulo,
        mensaje,
        bg="#F1F5F9",
        title_fg="#0F2D6B",
        prompt_text="Contrasena admin:",
        button_style="Create.TButton",
        confirm_text="Confirmar",
        geometry="380x210",
        wraplength=340,
    )


class BackupWindow:
    """Ventana principal de backup y restauracion."""

    def __init__(self, master, db, usuario):
        self.db = db
        self.usuario = usuario
        self.storage = BackupStorage(__file__)

        self.win = tk.Toplevel(master)
        self.win.title("Backup y Restauracion")
        self.win.configure(bg="#F1F5F9")
        self.win.grab_set()
        configurar_ventana(self.win, width=980, height=700, min_width=860, min_height=620)
        self._build()
        self._actualizar_lista()

    def _build(self):
        hdr = tk.Frame(self.win, bg="#0F2D6B", height=54)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(
            hdr,
            text="Backup y Restauracion de Base de Datos",
            font=("Segoe UI", 12, "bold"),
            bg="#0F2D6B",
            fg="white",
        ).pack(side=tk.LEFT, padx=16)
        body = tk.Frame(self.win, bg="#F1F5F9")
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        izq = tk.Frame(body, bg="#F1F5F9", width=220)
        izq.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        izq.pack_propagate(False)

        def sec_label(txt):
            tk.Label(
                izq,
                text=txt,
                font=("Segoe UI", 8, "bold"),
                bg="#F1F5F9",
                fg="#64748B",
                anchor="w",
            ).pack(fill=tk.X, pady=(12, 4))

        def btn(txt, cmd, style="Create.TButton"):
            ttk.Button(izq, text=txt, command=cmd, style=style).pack(fill=tk.X, pady=2)

        sec_label("CREAR BACKUP")
        btn("Crear backup ahora", self._crear_backup)
        btn("Guardar en otra ubicacion", self._crear_backup_custom, style="Neutral.TButton")

        sec_label("RESTAURAR")
        btn("Restaurar backup seleccionado", self._restaurar_seleccionado, style="Warn.TButton")
        btn("Restaurar desde archivo...", self._restaurar_externo, style="Neutral.TButton")

        sec_label("GESTION")
        btn("Eliminar backup seleccionado", self._eliminar_seleccionado, style="Delete.TButton")
        btn("Actualizar lista", self._actualizar_lista, style="Neutral.TButton")

        tk.Label(
            izq,
            text=f"Se conservan los ultimos\n{MAX_BACKUPS} backups automaticamente.",
            font=("Segoe UI", 8),
            bg="#F1F5F9",
            fg="#94A3B8",
            justify="left",
            wraplength=200,
        ).pack(pady=(16, 0), anchor="w")

        der = tk.Frame(body, bg="#F1F5F9")
        der.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(
            der,
            text="Backups guardados",
            font=("Segoe UI", 10, "bold"),
            bg="#F1F5F9",
            fg="#1E293B",
        ).pack(anchor="w", pady=(0, 6))

        frm_t = ttk.Frame(der)
        frm_t.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(frm_t)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        cols = ("Archivo", "Tamano", "Fecha")
        self.tree = ttk.Treeview(
            frm_t,
            columns=cols,
            show="headings",
            yscrollcommand=sb.set,
            height=16,
        )
        sb.config(command=self.tree.yview)
        for col, width, anchor in zip(cols, [360, 80, 130], ["w", "center", "center"]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=anchor)
        self.tree.tag_configure("auto", background="#EFF6FF")
        self.tree.tag_configure("manual", background="#F0FDF4")
        self.tree.pack(fill=tk.BOTH, expand=True)
        bloquear_columnas(self.tree)

        ley = tk.Frame(der, bg="#F1F5F9")
        ley.pack(fill=tk.X, pady=(6, 0))
        for color, texto in [("#EFF6FF", "Automatico"), ("#F0FDF4", "Manual")]:
            tk.Frame(ley, bg=color, width=14, height=14, relief="flat").pack(side=tk.LEFT)
            tk.Label(
                ley,
                text=texto,
                font=("Segoe UI", 8),
                bg="#F1F5F9",
                fg="#64748B",
            ).pack(side=tk.LEFT, padx=(3, 10))

        self.lbl_total = tk.Label(
            der,
            text="",
            font=("Segoe UI", 8),
            bg="#F1F5F9",
            fg="#64748B",
        )
        self.lbl_total.pack(anchor="e", pady=(2, 0))

    def _actualizar_lista(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        backups = self.storage.list_backups()
        for item in backups:
            self.tree.insert(
                "",
                tk.END,
                iid=item["path"],
                tags=(item["tag"],),
                values=(item["name"], f"{item['size_kb']} KB", item["modified"]),
            )

        total_kb = sum(item["size_kb"] for item in backups)
        self.lbl_total.config(text=f"{len(backups)} archivo(s)  -  {total_kb:.1f} KB total")

    def _seleccionado(self):
        sel = self.tree.selection()
        if not sel:
            return None, None
        ruta = sel[0]
        nombre = self.tree.item(sel[0])["values"][0]
        return nombre, ruta

    def _crear_backup(self):
        if not _pedir_password(
            self.win,
            self.db,
            self.usuario["id"],
            "Confirmar backup",
            "Ingrese su contrasena para crear el backup.",
        ):
            return
        ruta = self.storage.build_timestamped_path("manual")
        self._ejecutar_backup(ruta, tipo="manual en carpeta backups/")

    def _crear_backup_custom(self):
        if not _pedir_password(
            self.win,
            self.db,
            self.usuario["id"],
            "Confirmar backup",
            "Ingrese su contrasena para crear el backup.",
        ):
            return
        ruta = filedialog.asksaveasfilename(
            parent=self.win,
            defaultextension=".sql",
            filetypes=[("SQL", "*.sql"), ("Todos", "*.*")],
            initialfile=os.path.basename(self.storage.build_timestamped_path("backup")),
        )
        if not ruta:
            return
        self._ejecutar_backup(ruta, tipo=f"manual en {ruta}")

    def _ejecutar_backup(self, ruta, tipo):
        ok, resultado = self.db.backup_base_datos(ruta)
        if not ok:
            messagebox.showerror(
                "Error",
                f"No se pudo crear el backup:\n{resultado}",
                parent=self.win,
            )
            return

        self.storage.cleanup_old_backups()
        self.db.registrar_log(
            self.usuario["id"],
            self.usuario["username"],
            "Crear backup",
            f"Tipo: {tipo} | Archivo: {os.path.basename(ruta)}",
        )
        messagebox.showinfo(
            "Backup creado",
            "Backup guardado exitosamente.\n\n"
            f"Archivo: {os.path.basename(ruta)}\n"
            f"Ubicacion: {os.path.dirname(ruta)}",
            parent=self.win,
        )
        self._actualizar_lista()

    def _restaurar_seleccionado(self):
        nombre, ruta = self._seleccionado()
        if not nombre:
            messagebox.showwarning("Aviso", "Seleccione un backup de la lista.", parent=self.win)
            return
        self._flujo_restaurar(nombre, ruta)

    def _restaurar_externo(self):
        if not _pedir_password(
            self.win,
            self.db,
            self.usuario["id"],
            "Verificar identidad",
            "Ingrese su contrasena antes de seleccionar el archivo a restaurar.",
        ):
            return
        ruta = filedialog.askopenfilename(
            parent=self.win,
            title="Seleccionar archivo de backup",
            filetypes=[("SQL", "*.sql"), ("Todos", "*.*")],
        )
        if not ruta:
            return
        self._flujo_restaurar(os.path.basename(ruta), ruta, pwd_verificado=True)

    def _flujo_restaurar(self, nombre, ruta, pwd_verificado=False):
        if not pwd_verificado and not _pedir_password(
            self.win,
            self.db,
            self.usuario["id"],
            "Verificar identidad",
            f"Ingrese su contrasena para iniciar la restauracion de '{nombre}'.",
        ):
            return

        if not messagebox.askyesno(
            "Restaurar base de datos",
            f"Va a restaurar el backup:\n  {nombre}\n\n"
            "ADVERTENCIA: Esta accion reemplazara todos los datos actuales.\n"
            "La operacion no se puede deshacer.\n\n"
            "Desea continuar?",
            icon="warning",
            parent=self.win,
        ):
            return

        resp = messagebox.askyesnocancel(
            "Backup de seguridad",
            "Se recomienda crear un backup de los datos actuales antes de restaurar.\n\n"
            "Crear backup de seguridad ahora?",
            parent=self.win,
        )
        if resp is None:
            return
        if resp:
            ruta_seg = self.storage.build_timestamped_path("previo_restauracion")
            ok, _ = self.db.backup_base_datos(ruta_seg)
            if ok:
                messagebox.showinfo(
                    "Backup creado",
                    f"Backup de seguridad guardado:\n{os.path.basename(ruta_seg)}",
                    parent=self.win,
                )
                self._actualizar_lista()
            else:
                if not messagebox.askyesno(
                    "No se pudo crear el backup",
                    "No se pudo crear el backup de seguridad.\n"
                    "Desea continuar la restauracion de todas formas?",
                    parent=self.win,
                ):
                    return

        if not _pedir_password(
            self.win,
            self.db,
            self.usuario["id"],
            "Confirmacion final",
            "Confirme su contrasena una ultima vez para ejecutar la restauracion.",
        ):
            return

        self._ejecutar_restauracion(nombre, ruta)

    def _ejecutar_restauracion(self, nombre, ruta):
        ok, resultado = self.db.restaurar_base_datos_desde_sql(ruta)
        if not ok:
            messagebox.showerror(
                "Error en restauracion",
                f"No se pudo restaurar el backup:\n{resultado}",
                parent=self.win,
            )
            return

        errores = resultado
        self.db.registrar_log(
            self.usuario["id"],
            self.usuario["username"],
            "Restaurar backup",
            f"Archivo: {nombre} | Errores: {len(errores)}",
        )

        if errores:
            detalle = "\n".join(f"- {err}" for err in errores[:5])
            if len(errores) > 5:
                detalle += "\n..."
            messagebox.showwarning(
                "Restauracion con advertencias",
                f"Restauracion completada con {len(errores)} advertencia(s).\n\n"
                f"Primeras advertencias:\n{detalle}\n\n"
                "Cierre sesion y vuelva a entrar para ver los datos actualizados.",
                parent=self.win,
            )
            return

        messagebox.showinfo(
            "Restauracion exitosa",
            "Base de datos restaurada correctamente.\n\n"
            f"Archivo: {nombre}\n\n"
            "Cierre sesion y vuelva a entrar para ver los datos actualizados.",
            parent=self.win,
        )

    def _eliminar_seleccionado(self):
        nombre, ruta = self._seleccionado()
        if not nombre:
            messagebox.showwarning("Aviso", "Seleccione un backup de la lista.", parent=self.win)
            return

        if not messagebox.askyesno(
            "Eliminar backup",
            f"Eliminar el archivo de backup?\n\n  {nombre}\n\n"
            "Esta accion no se puede deshacer.",
            parent=self.win,
        ):
            return

        if not _pedir_password(
            self.win,
            self.db,
            self.usuario["id"],
            "Confirmar eliminacion",
            f"Ingrese su contrasena para eliminar el backup '{nombre}'.",
        ):
            return

        try:
            self.storage.delete_backup(ruta)
            self.db.registrar_log(
                self.usuario["id"],
                self.usuario["username"],
                "Eliminar backup",
                f"Archivo: {nombre}",
            )
            messagebox.showinfo("Correcto", f"Backup '{nombre}' eliminado.", parent=self.win)
            self._actualizar_lista()
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self.win)
