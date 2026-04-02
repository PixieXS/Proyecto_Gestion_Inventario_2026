from mysql.connector import Error


def _valor_sql(valor):
    return None if valor == '' else valor


class MovimientosMixin:

    def registrar_movimiento(self, id_producto, tipo_movimiento, cantidad,
                             descripcion="", id_usuario=None):
        try:
            tipo_lower = tipo_movimiento.lower()
            if tipo_lower == "salida":
                # UPDATE atómico: solo descuenta si hay stock suficiente
                # Evita stock negativo cuando múltiples usuarios operan al mismo tiempo
                self.cursor.execute("""
                    UPDATE productos
                    SET cantidad = cantidad - %s
                    WHERE id = %s AND cantidad >= %s AND activo = 1
                """, (cantidad, id_producto, cantidad))

                if self.cursor.rowcount == 0:
                    self.cursor.execute(
                        "SELECT cantidad, activo FROM productos WHERE id=%s", (id_producto,))
                    row = self.cursor.fetchone()
                    if not row:
                        return False, "Producto no encontrado"
                    if not row['activo']:
                        return False, "El producto está inhabilitado"
                    return False, (
                        f"⚠️ Stock insuficiente.\n"
                        f"Stock actual: {row['cantidad']} unidades\n"
                        f"Salida solicitada: {cantidad} unidades")
            elif tipo_lower == "entrada":
                self.cursor.execute(
                    "UPDATE productos SET cantidad = cantidad + %s WHERE id = %s",
                    (cantidad, id_producto))
            elif tipo_lower == "ajuste":
                self.cursor.execute(
                    "UPDATE productos SET cantidad = %s WHERE id = %s AND activo=1",
                    (cantidad, id_producto))
                if self.cursor.rowcount == 0:
                    return False, "Producto no encontrado o inhabilitado"
            else:
                self.cursor.execute(
                    "UPDATE productos SET cantidad = cantidad + %s WHERE id = %s",
                    (cantidad, id_producto))

            self.cursor.execute("""
                INSERT INTO movimientos
                (id_producto, tipo_movimiento, cantidad, descripcion, id_usuario)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_producto, tipo_movimiento, cantidad, descripcion, id_usuario))
            self.connection.commit()
            return True, "Movimiento registrado exitosamente"
        except Error as e:
            return False, str(e)

    def obtener_movimientos(self, id_producto=None):
        try:
            if id_producto:
                self.cursor.execute(
                    "SELECT * FROM movimientos WHERE id_producto=%s ORDER BY fecha DESC",
                    (id_producto,))
            else:
                self.cursor.execute("SELECT * FROM movimientos ORDER BY fecha DESC")
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def obtener_historial_producto(self, id_producto):
        try:
            self.ping_and_commit()
            self.cursor.execute("""
                SELECT m.id,
                       m.id_producto,
                       m.tipo_movimiento,
                       m.cantidad,
                       m.fecha,
                       m.descripcion,
                       m.id_usuario,
                       COALESCE(u.username, 'Sistema') AS usuario
                FROM movimientos m
                LEFT JOIN usuarios u ON m.id_usuario = u.id
                WHERE m.id_producto = %s
                ORDER BY m.fecha DESC, m.id DESC
            """, (id_producto,))
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def obtener_movimientos_rango(self, fecha_inicio, fecha_fin,
                                  categoria='', id_proveedor=None, tipo=''):
        try:
            cond = ["DATE(m.fecha) BETWEEN %s AND %s"]
            params = [fecha_inicio, fecha_fin]
            if categoria and categoria != 'Todas':
                cond.append("p.categoria = %s"); params.append(categoria)
            if id_proveedor:
                cond.append("p.id_proveedor = %s"); params.append(id_proveedor)
            if tipo and tipo != 'Todos':
                cond.append("m.tipo_movimiento = %s"); params.append(tipo)
            self.cursor.execute(f"""
                SELECT m.*, p.nombre AS nombre_producto,
                       p.categoria AS categoria_producto,
                       u.username AS usuario_nombre
                FROM movimientos m
                JOIN productos p ON m.id_producto = p.id
                LEFT JOIN usuarios u ON m.id_usuario = u.id
                WHERE {' AND '.join(cond)}
                ORDER BY m.fecha DESC
            """, params)
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def buscar_movimientos(self, termino='', tipo='', categoria='', fecha_desde='', fecha_hasta=''):
        """Búsqueda en tiempo real de movimientos con múltiples filtros."""
        try:
            cond, params = [], []
            if termino:
                cond.append("(p.nombre LIKE %s OR m.descripcion LIKE %s)")
                params += [f"%{termino}%", f"%{termino}%"]
            if tipo and tipo != 'Todos':
                cond.append("m.tipo_movimiento = %s"); params.append(tipo)
            if categoria and categoria != 'Todas':
                cond.append("p.categoria = %s"); params.append(categoria)
            if fecha_desde:
                cond.append("DATE(m.fecha) >= %s"); params.append(fecha_desde)
            if fecha_hasta:
                cond.append("DATE(m.fecha) <= %s"); params.append(fecha_hasta)
            where = ("WHERE " + " AND ".join(cond)) if cond else ""
            self.cursor.execute(f"""
                SELECT m.*, p.nombre AS nombre_producto,
                       p.categoria AS categoria_producto,
                       u.username AS usuario_nombre
                FROM movimientos m
                JOIN productos p ON m.id_producto = p.id
                LEFT JOIN usuarios u ON m.id_usuario = u.id
                {where}
                ORDER BY m.fecha DESC
                LIMIT 500
            """, params)
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

