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
        
        #-- Estado De Productos Y Estadisticas

    def inhabilitar_producto(self, id_producto):
        try:
            self.cursor.execute(
                "SELECT cantidad, nombre FROM productos WHERE id=%s", (id_producto,))
            row = self.cursor.fetchone()
            if not row:
                return False, "Producto no encontrado"
            if row['cantidad'] > 0:
                return False, (
                    f"No se puede inhabilitar '{row['nombre']}'.\n"
                    f"Aún tiene {row['cantidad']} unidades en stock.\n"
                    f"Solo se puede inhabilitar con stock en 0.")
            self.cursor.execute(
                "UPDATE productos SET activo=0 WHERE id=%s", (id_producto,))
            self.connection.commit()
            return True, f"Producto '{row['nombre']}' inhabilitado correctamente."
        except Error as e:
            return False, str(e)

    def habilitar_producto(self, id_producto):
        try:
            self.cursor.execute(
                "SELECT nombre FROM productos WHERE id=%s", (id_producto,))
            row = self.cursor.fetchone()
            if not row:
                return False, "Producto no encontrado"
            self.cursor.execute(
                "UPDATE productos SET activo=1 WHERE id=%s", (id_producto,))
            self.connection.commit()
            return True, f"Producto '{row['nombre']}' habilitado correctamente."
        except Error as e:
            return False, str(e)

    def obtener_productos_inactivos(self):
        try:
            self.ping_and_commit()
            self.cursor.execute(
                "SELECT * FROM productos WHERE activo=0 ORDER BY nombre")
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def obtener_productos_criticos(self):
        try:
            self.cursor.execute("""
                SELECT id, nombre, cantidad, stock_minimo, proveedor
                FROM productos
                WHERE cantidad <= stock_minimo AND activo=1
                ORDER BY (cantidad - stock_minimo) ASC
            """)
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def obtener_estadisticas(self):
        try:
            self.ping_and_commit()
            stats = {}
            self.cursor.execute("SELECT COUNT(*) AS n FROM productos WHERE activo=1")
            stats['total_productos'] = self.cursor.fetchone()['n']
            self.cursor.execute("SELECT SUM(cantidad) AS s FROM productos WHERE activo=1")
            stats['stock_total'] = self.cursor.fetchone()['s'] or 0
            self.cursor.execute(
                "SELECT SUM(cantidad*precio_unitario) AS v FROM productos WHERE activo=1")
            r = self.cursor.fetchone()
            stats['valor_total'] = float(r['v']) if r['v'] else 0.0
            self.cursor.execute(
                "SELECT COUNT(*) AS n FROM productos WHERE cantidad<=stock_minimo AND activo=1")
            stats['bajo_stock'] = self.cursor.fetchone()['n']
            self.cursor.execute("SELECT COUNT(*) AS n FROM proveedores")
            stats['total_proveedores'] = self.cursor.fetchone()['n']
            self.cursor.execute("SELECT COUNT(*) AS n FROM productos WHERE activo=0")
            stats['productos_inactivos'] = self.cursor.fetchone()['n']
            return stats
        except Error as e:
            print(e); return {}
        
        #-- Historial De Precios Y Reportes Por Proveedor
         
    def registrar_cambio_precio(self, id_producto, precio_anterior, precio_nuevo,
                                 id_usuario, username):
        """Guarda en historial cuando el precio de un producto cambia."""
        try:
            if float(precio_anterior) == float(precio_nuevo):
                return  # sin cambio, no registrar
            self.cursor.execute("""
                INSERT INTO historial_precios
                (id_producto, precio_anterior, precio_nuevo, id_usuario, username)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_producto, precio_anterior, precio_nuevo, id_usuario, username))
            self.connection.commit()
        except Exception as e:
            print(f"[WARN] historial_precios: {e}")

    def obtener_historial_precios(self, id_producto):
        """Retorna el historial de cambios de precio de un producto."""
        try:
            self.cursor.execute("""
                SELECT hp.precio_anterior, hp.precio_nuevo,
                       hp.username, hp.fecha,
                       (hp.precio_nuevo - hp.precio_anterior) AS diferencia
                FROM historial_precios hp
                WHERE hp.id_producto = %s
                ORDER BY hp.fecha DESC
            """, (id_producto,))
            return self.cursor.fetchall()
        except Exception as e:
            print(e); return []

    def reporte_por_proveedor(self, id_proveedor=None):
        """Retorna resumen de productos agrupados por proveedor con totales."""
        try:
            if id_proveedor:
                self.cursor.execute("""
                    SELECT p.nombre AS proveedor,
                           pr.ruc_nit, pr.telefono, pr.correo,
                           COUNT(prod.id) AS total_productos,
                           SUM(prod.cantidad) AS stock_total,
                           SUM(prod.cantidad * prod.precio_unitario) AS valor_total,
                           SUM(CASE WHEN prod.cantidad <= prod.stock_minimo THEN 1 ELSE 0 END) AS criticos
                    FROM proveedores p
                    LEFT JOIN productos prod ON prod.id_proveedor = p.id AND prod.activo=1
                    WHERE p.id = %s
                    GROUP BY p.id
                """, (id_proveedor,))
            else:
                self.cursor.execute("""
                    SELECT p.nombre AS proveedor,
                           p.id AS id_proveedor,
                           p.ruc_nit, p.telefono, p.correo,
                           COUNT(prod.id) AS total_productos,
                           COALESCE(SUM(prod.cantidad), 0) AS stock_total,
                           COALESCE(SUM(prod.cantidad * prod.precio_unitario), 0) AS valor_total,
                           SUM(CASE WHEN prod.cantidad <= prod.stock_minimo THEN 1 ELSE 0 END) AS criticos
                    FROM proveedores p
                    LEFT JOIN productos prod ON prod.id_proveedor = p.id AND prod.activo=1
                    WHERE p.activo=1
                    GROUP BY p.id
                    ORDER BY valor_total DESC
                """)
            return self.cursor.fetchall()
        except Exception as e:
            print(e); return []

    def obtener_productos_detalle_proveedor(self, id_proveedor):
        """Lista de productos de un proveedor específico con todos los datos."""
        try:
            self.cursor.execute("""
                SELECT nombre, codigo, cantidad, stock_minimo, stock_maximo,
                       precio_unitario, categoria, unidad_medida,
                       (cantidad * precio_unitario) AS valor_total
                FROM productos
                WHERE id_proveedor=%s AND activo=1
                ORDER BY nombre
            """, (id_proveedor,))
            return self.cursor.fetchall()
        except Exception as e:
            print(e); return []
