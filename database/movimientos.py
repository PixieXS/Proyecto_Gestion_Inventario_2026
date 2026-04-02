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

    def importar_productos_excel(self, productos_lista, modo_duplicados='saltar'):
        from modulos.campos_opcionales import obtener_campos_activos

        insertados, actualizados, omitidos, errores = 0, 0, 0, []
        cache_proveedores = {}
        campos_opcionales = obtener_campos_activos(self)
        keys_opcionales = [c['key'] for c in campos_opcionales]

        # ── PASO 1: crear TODAS las categorías nuevas del Excel de una vez ────
        cats_en_excel = set()
        for p in productos_lista:
            cat = str(p.get('categoria', '') or '').strip()
            if cat:
                cats_en_excel.add(cat)
        self.cursor.execute("SELECT nombre FROM categorias")
        cats_en_bd = {r['nombre'].strip() for r in self.cursor.fetchall()}

        cats_nuevas = cats_en_excel - cats_en_bd
        if cats_nuevas:
            for cat_nueva in sorted(cats_nuevas):
                self.cursor.execute(
                    "INSERT INTO categorias (nombre) VALUES (%s)", (cat_nueva,))
            self.connection.commit()   # commit dedicado solo a categorías

        # Recargar cache completo (existentes + recién creadas)
        self.cursor.execute("SELECT nombre FROM categorias")
        cache_categorias = {r['nombre'].strip() for r in self.cursor.fetchall()}

        # ── PASO 2: importar productos ────────────────────────────────────────
        for i, p in enumerate(productos_lista, start=2):
            try:
                nombre = str(p.get('nombre', '')).strip()
                codigo = str(p.get('codigo', '')).strip() or None
                if not nombre:
                    errores.append((i, "Nombre vacío")); continue

                cantidad = int(float(p.get('cantidad', 0)))
                precio   = float(p.get('precio_unitario', 0))
                if precio < 0 or cantidad < 0:
                    errores.append((i, "Cantidad o precio negativo")); continue

                descripcion = str(p.get('descripcion', '')).strip()
                nombre_prov = str(p.get('proveedor', '')).strip()
                categoria   = str(p.get('categoria', '') or '').strip()
                if categoria and categoria not in cache_categorias:
                    categoria = ''
                stock_min   = int(float(p.get('stock_minimo', 5)))
                stock_max   = int(float(p.get('stock_maximo', 0))) or None
                unidad      = str(p.get('unidad_medida', 'Unidad') or 'Unidad').strip()
                precio_compra_raw = p.get('precio_compra')
                precio_compra = None
                if str(precio_compra_raw if precio_compra_raw is not None else '').strip():
                    precio_compra = float(precio_compra_raw)
                    if precio_compra < 0:
                        errores.append((i, "Precio de compra negativo")); continue
                extras      = {k: p.get(k) for k in keys_opcionales if k in p}

                # ── Resolver proveedor ────────────────────────────────────────
                id_proveedor = None
                if nombre_prov:
                    if nombre_prov in cache_proveedores:
                        id_proveedor = cache_proveedores[nombre_prov]
                    else:
                        self.cursor.execute(
                            "SELECT id FROM proveedores WHERE nombre=%s", (nombre_prov,))
                        row_prov = self.cursor.fetchone()
                        if row_prov:
                            id_proveedor = row_prov['id']
                        else:
                            self.cursor.execute(
                                "INSERT INTO proveedores (nombre) VALUES (%s)", (nombre_prov,))
                            id_proveedor = self.cursor.lastrowid
                        cache_proveedores[nombre_prov] = id_proveedor

                # ── Detectar duplicado: código primero, luego nombre ──────────
                existente = None
                if codigo:
                    self.cursor.execute(
                        "SELECT id FROM productos WHERE codigo=%s AND activo=1", (codigo,))
                    existente = self.cursor.fetchone()
                if not existente:
                    self.cursor.execute(
                        "SELECT id FROM productos WHERE nombre=%s AND activo=1", (nombre,))
                    existente = self.cursor.fetchone()

                if existente:
                    if modo_duplicados == 'actualizar':
                        sets = [
                            "nombre=%s", "codigo=%s", "descripcion=%s", "cantidad=%s",
                            "precio_unitario=%s", "precio_compra=%s", "proveedor=%s", "id_proveedor=%s",
                            "categoria=%s", "stock_minimo=%s", "stock_maximo=%s",
                            "unidad_medida=%s", "ultima_actualizacion=CURRENT_TIMESTAMP"
                        ]
                        vals = [
                            nombre, codigo, descripcion, cantidad, precio,
                            _valor_sql(precio_compra), nombre_prov, id_proveedor, categoria, stock_min,
                            stock_max, unidad
                        ]
                        for k, v in extras.items():
                            sets.append(f"`{k}`=%s")
                            vals.append(_valor_sql(v))
                        vals.append(existente['id'])
                        self.cursor.execute(
                            f"UPDATE productos SET {', '.join(sets)} WHERE id=%s", vals)
                        actualizados += 1
                    else:
                        omitidos += 1
                else:
                    cols = [
                        'nombre', 'codigo', 'descripcion', 'cantidad', 'precio_unitario',
                        'precio_compra', 'proveedor', 'id_proveedor', 'categoria', 'stock_minimo',
                        'stock_maximo', 'unidad_medida'
                    ]
                    vals = [
                        nombre, codigo, descripcion, cantidad, precio,
                        _valor_sql(precio_compra), nombre_prov, id_proveedor, categoria, stock_min,
                        stock_max, unidad
                    ]
                    for k, v in extras.items():
                        cols.append(k)
                        vals.append(_valor_sql(v))
                    cols_sql = ', '.join(f"`{c}`" for c in cols)
                    ph_sql = ', '.join(['%s'] * len(vals))
                    self.cursor.execute(
                        f"INSERT INTO productos ({cols_sql}, activo) VALUES ({ph_sql}, 1)", vals)
                    insertados += 1

            except Exception as e:
                errores.append((i, str(e)))

        if insertados + actualizados > 0:
            self.connection.commit()

        return insertados, actualizados, omitidos, errores