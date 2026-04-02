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
