from mysql.connector import Error


def _valor_sql(valor):
    return None if valor == '' else valor


class ProductosMixin:

    def crear_producto(self, nombre, descripcion, cantidad, precio_unitario,
                       proveedor, categoria='', stock_minimo=5,
                       id_proveedor=None, unidad_medida='Unidad', stock_maximo=None,
                       precio_compra=None, codigo=None, extras=None):
        try:
            if stock_maximo is not None and cantidad > stock_maximo:
                return False, f"La cantidad ({cantidad}) supera el stock máximo ({stock_maximo})."
            cols  = ['nombre','codigo','descripcion','cantidad','precio_unitario',
                     'precio_compra','proveedor','categoria','stock_minimo',
                     'id_proveedor','unidad_medida','stock_maximo']
            vals  = [nombre, codigo or None, descripcion, cantidad, precio_unitario,
                     _valor_sql(precio_compra), proveedor, categoria, stock_minimo,
                     id_proveedor or None, unidad_medida or 'Unidad', _valor_sql(stock_maximo)]
            if extras:
                for k, v in extras.items():
                    cols.append(k); vals.append(_valor_sql(v))
            cols_str = ', '.join(f'`{c}`' for c in cols)
            phs      = ', '.join(['%s'] * len(vals))
            self.cursor.execute(
                f"INSERT INTO productos ({cols_str}, activo) VALUES ({phs}, 1)",
                vals)
            self.connection.commit()
            return True, "Producto creado exitosamente"
        except Error as e:
            return False, str(e)

    def obtener_productos(self, solo_activos=True):
        try:
            self.ping_and_commit()
            if solo_activos:
                self.cursor.execute(
                    "SELECT * FROM productos WHERE activo=1 ORDER BY fecha_registro DESC")
            else:
                self.cursor.execute("SELECT * FROM productos ORDER BY fecha_registro DESC")
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def buscar_productos(self, termino='', categoria='', solo_activos=True, proveedor=''):
        try:
            self.ping_and_commit()
            cond, params = [], []
            if solo_activos:
                cond.append("activo=1")
            if termino:
                cond.append("(nombre LIKE %s OR proveedor LIKE %s OR codigo LIKE %s)")
                params += [f"%{termino}%", f"%{termino}%", f"%{termino}%"]
            if categoria and categoria != 'Todas':
                cond.append("categoria=%s")
                params.append(categoria)
            if proveedor and proveedor != 'Todos':
                cond.append("proveedor=%s")
                params.append(proveedor)
            where = ("WHERE " + " AND ".join(cond)) if cond else ""
            self.cursor.execute(
                f"SELECT * FROM productos {where} ORDER BY fecha_registro DESC", params)
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def obtener_producto(self, id_producto):
        try:
            self.cursor.execute("SELECT * FROM productos WHERE id=%s", (id_producto,))
            return self.cursor.fetchone()
        except Error as e:
            print(e); return None

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

        # CRUD Productos
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

    def actualizar_producto(self, id_producto, nombre, descripcion, cantidad,
                            precio_unitario, proveedor, categoria='',
                            stock_minimo=5, id_proveedor=None, codigo=None,
                            unidad_medida='Unidad', stock_maximo=None,
                            precio_compra=None, extras=None):
        try:
            if stock_maximo is not None and cantidad > stock_maximo:
                return False, f"La cantidad ({cantidad}) supera el stock máximo ({stock_maximo})."
            sets = [
                "nombre=%s","codigo=%s","descripcion=%s","cantidad=%s",
                "precio_unitario=%s","precio_compra=%s","proveedor=%s","categoria=%s",
                "stock_minimo=%s","id_proveedor=%s","unidad_medida=%s","stock_maximo=%s",
                "ultima_actualizacion=CURRENT_TIMESTAMP"]
            vals = [nombre, codigo or None, descripcion, cantidad, precio_unitario,
                    _valor_sql(precio_compra), proveedor, categoria, stock_minimo,
                    id_proveedor or None, unidad_medida or 'Unidad', _valor_sql(stock_maximo)]
            if extras:
                for k, v in extras.items():
                    sets.append(f"`{k}`=%s"); vals.append(_valor_sql(v))
            vals.append(id_producto)
            self.cursor.execute(
                f"UPDATE productos SET {', '.join(sets)} WHERE id=%s", vals)
            self.connection.commit()
            return True, "Producto actualizado exitosamente"
        except Error as e:
            return False, str(e)

   