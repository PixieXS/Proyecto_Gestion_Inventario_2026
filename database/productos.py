from mysql.connector import Error


def _valor_sql(valor):
    return None if valor == '' else valor


class ProductosMixin:

    def obtener_categorias(self):
        """Retorna todas las categorías para la pantalla de gestión."""
        try:
            self.cursor.execute("SELECT id, nombre, descripcion FROM categorias ORDER BY nombre")
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def obtener_nombres_categorias(self):
        """Retorna solo los nombres de categorías ACTIVAS para usar en comboboxes."""
        try:
            self.cursor.execute(
                "SELECT nombre FROM categorias WHERE activa=1 ORDER BY nombre")
            return [r['nombre'] for r in self.cursor.fetchall()]
        except Error as e:
            print(e); return []

    def contar_categorias(self):
        try:
            self.cursor.execute("SELECT COUNT(*) AS n FROM categorias")
            return self.cursor.fetchone()['n']
        except Error:
            return 0

    def contar_productos_activos_por_categoria(self, categoria):
        try:
            self.cursor.execute(
                "SELECT COUNT(*) AS n FROM productos WHERE categoria=%s AND activo=1",
                (categoria,))
            return self.cursor.fetchone()['n']
        except Error:
            return 0

    def crear_categoria(self, nombre, descripcion=''):
        try:
            self.cursor.execute(
                "INSERT INTO categorias (nombre, descripcion) VALUES (%s, %s)",
                (nombre.strip(), descripcion.strip()))
            self.connection.commit()
            return True, "Categoría creada"
        except Error as e:
            return False, str(e)

    def actualizar_categoria(self, id_cat, nombre, descripcion=''):
        try:
            self.cursor.execute(
                "UPDATE categorias SET nombre=%s, descripcion=%s WHERE id=%s",
                (nombre.strip(), descripcion.strip(), id_cat))
            self.connection.commit()
            return True, "Categoría actualizada"
        except Error as e:
            return False, str(e)

    def eliminar_categoria(self, id_cat):
        """Elimina una categoría solo si no tiene productos activos asignados."""
        try:
            self.cursor.execute("SELECT nombre FROM categorias WHERE id=%s", (id_cat,))
            row = self.cursor.fetchone()
            if not row:
                return False, "Categoría no encontrada"
            n = self.contar_productos_activos_por_categoria(row['nombre'])
            if n > 0:
                return False, (f"No se puede eliminar: {n} producto(s) usan esta categoría.\n"
                               f"Cambie la categoría de esos productos primero.")
            self.cursor.execute("DELETE FROM categorias WHERE id=%s", (id_cat,))
            self.connection.commit()
            return True, f"Categoría '{row['nombre']}' eliminada correctamente."
        except Error as e:
            return False, str(e)
