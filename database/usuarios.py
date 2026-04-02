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

  