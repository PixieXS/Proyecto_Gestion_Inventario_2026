from mysql.connector import Error
from .security import hash_password, needs_rehash, verify_password


def _hash(password: str) -> str:
    return hash_password(password)


def _verificar_password(password: str, stored: str) -> bool:
    return verify_password(password, stored)


class UsuariosMixin:

    # ── Autenticación ─────────────────────────────────────────────────────────

    def autenticar_usuario(self, username, password):
        try:
            self.cursor.execute("""
                SELECT u.id, u.username, u.nombre_completo, u.activo,
                       u.password_hash,
                       r.id AS id_rol, r.nombre AS rol
                FROM usuarios u
                JOIN roles r ON u.id_rol = r.id
                WHERE u.username = %s
            """, (username,))
            usuario = self.cursor.fetchone()
            if not usuario:
                return None, "Usuario o contraseña incorrectos"
            if not _verificar_password(password, usuario['password_hash']):
                return None, "Usuario o contraseña incorrectos"
            if not usuario['activo']:
                return None, "Usuario desactivado. Contacte al administrador."
            try:
                if needs_rehash(usuario['password_hash']):
                    self.cursor.execute(
                        "UPDATE usuarios SET password_hash=%s WHERE id=%s",
                        (hash_password(password), usuario['id']))
                self.cursor.execute(
                    "UPDATE usuarios SET ultimo_login=NOW() WHERE id=%s",
                    (usuario['id'],))
                self.connection.commit()
            except Exception:
                pass
            self.cursor.execute(
                "SELECT permiso FROM permisos WHERE id_rol = %s", (usuario['id_rol'],))
            usuario['permisos'] = [r['permiso'] for r in self.cursor.fetchall()]
            return usuario, None
        except Error as e:
            return None, str(e)

    def verificar_password_usuario(self, id_usuario, password):
        try:
            self.cursor.execute(
                "SELECT password_hash FROM usuarios WHERE id=%s", (id_usuario,))
            row = self.cursor.fetchone()
            if not row or not verify_password(password, row['password_hash']):
                return False
            if needs_rehash(row['password_hash']):
                self.cursor.execute(
                    "UPDATE usuarios SET password_hash=%s WHERE id=%s",
                    (hash_password(password), id_usuario))
                self.connection.commit()
            return True
        except Error:
            return False

    def actualizar_password_usuario(self, id_usuario, nueva_password):
        try:
            self.cursor.execute(
                "UPDATE usuarios SET password_hash=%s WHERE id=%s",
                (hash_password(nueva_password), id_usuario))
            self.connection.commit()
            return True, "Contraseña actualizada"
        except Error as e:
            return False, str(e)

    def tiene_permiso(self, usuario, permiso):
        permisos = usuario.get('permisos', [])
        return 'all' in permisos or permiso in permisos

    # ── CRUD usuarios ─────────────────────────────────────────────────────────

    def obtener_usuarios(self):
        try:
            self.cursor.execute("""
                SELECT u.id, u.username, u.nombre_completo, u.activo,
                       u.ultimo_login,
                       r.nombre AS rol, u.fecha_creacion
                FROM usuarios u JOIN roles r ON u.id_rol = r.id
                ORDER BY u.id
            """)
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def crear_usuario(self, username, password, nombre_completo, id_rol):
        try:
            self.cursor.execute("""
                INSERT INTO usuarios (username, password_hash, nombre_completo, id_rol)
                VALUES (%s, %s, %s, %s)
            """, (username, hash_password(password), nombre_completo, id_rol))
            self.connection.commit()
            return True, "Usuario creado"
        except Error as e:
            return False, str(e)

    def actualizar_usuario(self, id_usuario, nombre_completo, id_rol, activo):
        try:
            self.cursor.execute("""
                UPDATE usuarios SET nombre_completo=%s, id_rol=%s, activo=%s WHERE id=%s
            """, (nombre_completo, id_rol, activo, id_usuario))
            self.connection.commit()
            return True, "Usuario actualizado"
        except Error as e:
            return False, str(e)

    def obtener_estado_usuario(self, id_usuario, default=1):
        try:
            self.cursor.execute(
                "SELECT activo FROM usuarios WHERE id=%s", (id_usuario,))
            row = self.cursor.fetchone()
            return row['activo'] if row else default
        except Error:
            return default

    def cambiar_password(self, id_usuario, password_actual, password_nueva):
        try:
            self.cursor.execute(
                "SELECT password_hash FROM usuarios WHERE id=%s", (id_usuario,))
            row = self.cursor.fetchone()
            if not row or not verify_password(password_actual, row['password_hash']):
                return False, "Contraseña actual incorrecta"
            return self.actualizar_password_usuario(id_usuario, password_nueva)
        except Error as e:
            return False, str(e)

    def reset_password_admin(self, id_usuario, nueva_password):
        """El administrador resetea la contraseña de otro usuario sin pedir la actual."""
        ok, msg = self.actualizar_password_usuario(id_usuario, nueva_password)
        return ok, "Contraseña reseteada exitosamente" if ok else msg

    def eliminar_usuario(self, id_usuario):
        try:
            self.cursor.execute("DELETE FROM usuarios WHERE id=%s", (id_usuario,))
            self.connection.commit()
            return True, "Usuario eliminado"
        except Error as e:
            return False, str(e)

    def contar_movimientos_usuario(self, id_usuario):
        try:
            self.cursor.execute(
                "SELECT COUNT(*) AS n FROM movimientos WHERE id_usuario=%s",
                (id_usuario,))
            return self.cursor.fetchone()['n']
        except Error:
            return 0

    def contar_logs_usuario(self, id_usuario):
        try:
            self.cursor.execute(
                "SELECT COUNT(*) AS n FROM log_actividad WHERE id_usuario=%s",
                (id_usuario,))
            return self.cursor.fetchone()['n']
        except Error:
            return 0

    def obtener_resumen_actividad_usuarios(self):
        try:
            self.cursor.execute("""
                SELECT u.id,
                       u.username,
                       u.nombre_completo,
                       u.activo,
                       u.ultimo_login,
                       u.fecha_creacion,
                       r.nombre AS rol,
                       COALESCE(m.n, 0) AS movimientos,
                       COALESCE(l.n, 0) AS acciones_log
                FROM usuarios u
                JOIN roles r ON u.id_rol = r.id
                LEFT JOIN (
                    SELECT id_usuario, COUNT(*) AS n
                    FROM movimientos
                    GROUP BY id_usuario
                ) m ON m.id_usuario = u.id
                LEFT JOIN (
                    SELECT id_usuario, COUNT(*) AS n
                    FROM log_actividad
                    GROUP BY id_usuario
                ) l ON l.id_usuario = u.id
                ORDER BY u.id
            """)
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    # ── Roles y permisos ──────────────────────────────────────────────────────

    def obtener_roles(self):
        try:
            self.cursor.execute("SELECT * FROM roles ORDER BY id")
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def obtener_permisos_rol(self, id_rol):
        try:
            self.cursor.execute("SELECT permiso FROM permisos WHERE id_rol=%s", (id_rol,))
            return [r['permiso'] for r in self.cursor.fetchall()]
        except Error as e:
            print(e); return []

    def actualizar_permisos_rol(self, id_rol, lista_permisos):
        try:
            self.cursor.execute("DELETE FROM permisos WHERE id_rol=%s", (id_rol,))
            for p in lista_permisos:
                self.cursor.execute(
                    "INSERT IGNORE INTO permisos (id_rol, permiso) VALUES (%s,%s)", (id_rol, p))
            self.connection.commit()
            return True, "Permisos actualizados"
        except Error as e:
            return False, str(e)

    def eliminar_rol(self, id_rol):
        try:
            self.cursor.execute(
                "SELECT COUNT(*) AS n FROM usuarios WHERE id_rol=%s", (id_rol,))
            asignados = self.cursor.fetchone()['n']
            if asignados > 0:
                return False, (
                    f"No se puede eliminar el rol porque tiene {asignados} usuario(s) asignado(s).\n"
                    "Reasigne esos usuarios a otro rol primero.")
            self.cursor.execute("DELETE FROM roles WHERE id=%s", (id_rol,))
            self.connection.commit()
            return True, "Rol eliminado"
        except Error as e:
            return False, str(e)
