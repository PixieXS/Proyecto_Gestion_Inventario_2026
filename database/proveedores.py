from mysql.connector import Error


class ProveedoresMixin:

    def obtener_proveedores(self, incluir_inactivos=False):
        try:
            self.ping_and_commit()
            if incluir_inactivos:
                self.cursor.execute("SELECT * FROM proveedores ORDER BY nombre")
            else:
                self.cursor.execute(
                    "SELECT * FROM proveedores WHERE activo=1 ORDER BY nombre")
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def obtener_proveedor(self, id_prov):
        try:
            self.cursor.execute("SELECT * FROM proveedores WHERE id=%s", (id_prov,))
            return self.cursor.fetchone()
        except Error as e:
            print(e); return None

    def contar_proveedores(self, incluir_inactivos=True):
        try:
            if incluir_inactivos:
                self.cursor.execute("SELECT COUNT(*) AS n FROM proveedores")
            else:
                self.cursor.execute(
                    "SELECT COUNT(*) AS n FROM proveedores WHERE activo=1")
            return self.cursor.fetchone()['n']
        except Error:
            return 0

    def contar_productos_activos_proveedor(self, id_prov):
        try:
            self.cursor.execute(
                "SELECT COUNT(*) AS n FROM productos WHERE id_proveedor=%s AND activo=1",
                (id_prov,))
            return self.cursor.fetchone()['n']
        except Error:
            return 0

    def crear_proveedor(self, nombre, telefono, correo, direccion,
                        contacto='', ruc_nit=''):
        try:
            self.cursor.execute("""
                INSERT INTO proveedores
                (nombre, telefono, correo, direccion, contacto, ruc_nit)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nombre, telefono, correo, direccion, contacto, ruc_nit))
            self.connection.commit()
            return True, "Proveedor creado"
        except Error as e:
            return False, str(e)

    def actualizar_proveedor(self, id_prov, nombre, telefono, correo, direccion,
                             contacto='', ruc_nit=''):
        try:
            self.cursor.execute("""
                UPDATE proveedores
                SET nombre=%s, telefono=%s, correo=%s, direccion=%s,
                    contacto=%s, ruc_nit=%s
                WHERE id=%s
            """, (nombre, telefono, correo, direccion, contacto, ruc_nit, id_prov))
            self.connection.commit()
            return True, "Proveedor actualizado"
        except Error as e:
            return False, str(e)

    def inhabilitar_proveedor(self, id_prov):
        try:
            n = self.contar_productos_activos_proveedor(id_prov)
            if n > 0:
                return False, (
                    f"Este proveedor tiene {n} producto(s) activo(s) asociado(s).\n"
                    f"Cambie el proveedor de esos productos primero.")
            self.cursor.execute(
                "UPDATE proveedores SET activo=0 WHERE id=%s", (id_prov,))
            self.connection.commit()
            return True, "Proveedor inhabilitado"
        except Error as e:
            return False, str(e)

    def habilitar_proveedor(self, id_prov):
        try:
            self.cursor.execute(
                "UPDATE proveedores SET activo=1 WHERE id=%s", (id_prov,))
            self.connection.commit()
            return True, "Proveedor habilitado"
        except Error as e:
            return False, str(e)

    def eliminar_proveedor(self, id_prov):
        try:
            self.cursor.execute("DELETE FROM proveedores WHERE id=%s", (id_prov,))
            self.connection.commit()
            return True, "Proveedor eliminado"
        except Error as e:
            return False, str(e)

    def obtener_productos_proveedor(self, id_prov):
        try:
            self.cursor.execute(
                "SELECT id, nombre FROM productos WHERE id_proveedor=%s AND activo=1",
                (id_prov,))
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []
