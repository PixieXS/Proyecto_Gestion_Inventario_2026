from collections import defaultdict
from datetime import datetime


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        try:
            return datetime(value.year, value.month, value.day)
        except TypeError:
            return datetime(value.year, value.month, value.day, value.hour, value.minute, value.second)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return None


def _as_date(value):
    dt = _as_datetime(value)
    return dt.date() if dt else None


class DynamicReportsService:
    AGGREGATIONS = {"Suma", "Promedio", "Maximo", "Minimo"}

    def __init__(self, owner, ctx, filtros_base):
        self.owner = owner
        self.ctx = ctx
        self.filtros_base = dict(filtros_base or {})
        self._optional_fields_cache = None

    def _field(self, key, label, data_type="text", fmt=None, *, chart_x=True, chart_y=None, default_selected=False):
        metric_types = {"number", "currency", "percent"}
        if chart_y is None:
            chart_y = data_type in metric_types
        return {
            "key": key,
            "label": label,
            "data_type": data_type,
            "format": fmt or (data_type if data_type in {"number", "currency", "percent", "date", "datetime"} else None),
            "chart_x": bool(chart_x),
            "chart_y": bool(chart_y),
            "default_selected": bool(default_selected),
            "filter_ops": self._filter_ops(data_type),
            "choices": [],
        }

    def _filter_ops(self, data_type):
        if data_type in {"number", "currency", "percent"}:
            return ["=", "!=", ">", ">=", "<", "<=", "Vacio", "Con valor"]
        if data_type in {"date", "datetime"}:
            return ["=", ">", ">=", "<", "<=", "Vacio", "Con valor"]
        return ["Es", "No es", "Contiene", "Empieza con", "Termina con", "Vacio", "Con valor"]

    def _optional_fields(self):
        if self._optional_fields_cache is not None:
            return list(self._optional_fields_cache)
        try:
            from modulos.campos_opcionales import obtener_campos_activos
        except Exception:
            self._optional_fields_cache = []
            return []

        tipos = {
            "peso": ("number", "number"),
            "garantia_meses": ("number", "number"),
            "fecha_vence": ("date", "date"),
            "impuesto_pct": ("percent", "percent"),
        }
        fields = []
        for campo in obtener_campos_activos(self.owner):
            data_type, fmt = tipos.get(campo.get("key"), ("text", None))
            fields.append(
                self._field(
                    campo.get("key"),
                    campo.get("label") or campo.get("key"),
                    data_type,
                    fmt,
                    chart_x=data_type in {"text", "date"},
                    chart_y=data_type in {"number", "percent"},
                )
            )
        self._optional_fields_cache = fields
        return list(fields)

    def _product_activity(self):
        activity = defaultdict(
            lambda: {
                "movimientos": 0,
                "entradas": 0,
                "salidas": 0,
                "ajustes": 0,
                "unidades_movidas": 0,
                "balance": 0,
                "ultima_actividad": None,
            }
        )
        for movimiento in self.ctx["movimientos_filtrados"]:
            pid = movimiento.get("id_producto")
            row = activity[pid]
            tipo = str(movimiento.get("tipo_resuelto") or "").lower()
            cantidad = _safe_int(movimiento.get("cantidad"))
            row["movimientos"] += 1
            row["unidades_movidas"] += cantidad
            if "entrada" in tipo:
                row["entradas"] += cantidad
                row["balance"] += cantidad
            elif "salida" in tipo:
                row["salidas"] += cantidad
                row["balance"] -= cantidad
            else:
                row["ajustes"] += cantidad
            fecha = movimiento.get("fecha_dt")
            if fecha and (row["ultima_actividad"] is None or fecha > row["ultima_actividad"]):
                row["ultima_actividad"] = fecha
        return activity

    def product_rows(self):
        activity = self._product_activity()
        rows = []
        for producto in self.ctx["productos_filtrados"]:
            cantidad = _safe_int(producto.get("cantidad"))
            stock_minimo = _safe_int(producto.get("stock_minimo"), 5)
            precio_venta = _safe_float(producto.get("precio_unitario"))
            precio_compra = _safe_float(producto.get("precio_compra"))
            valor_inventario = cantidad * precio_venta
            costo_inventario = cantidad * precio_compra
            margen_unitario = precio_venta - precio_compra
            margen_total = valor_inventario - costo_inventario
            margen_pct = ((margen_unitario / precio_compra) * 100) if precio_compra > 0 else None
            activity_row = activity.get(producto.get("id")) or {}

            row = {
                "registros": 1,
                "id": producto.get("id"),
                "codigo": producto.get("codigo") or "",
                "producto": producto.get("nombre") or "",
                "descripcion": producto.get("descripcion") or "",
                "categoria": producto.get("categoria_resuelta") or "General",
                "proveedor": producto.get("proveedor_resuelto") or "Sin proveedor",
                "unidad": producto.get("unidad_resuelta") or "Unidad",
                "estado": "Activo" if bool(producto.get("activo", 1)) else "Inactivo",
                "estado_stock": "Sin stock" if cantidad == 0 else ("Stock bajo" if cantidad <= stock_minimo else "Normal"),
                "stock_actual": cantidad,
                "stock_minimo": stock_minimo,
                "stock_maximo": _safe_int(producto.get("stock_maximo")) or None,
                "precio_compra": precio_compra or None,
                "precio_venta": precio_venta,
                "valor_inventario": valor_inventario,
                "costo_inventario": costo_inventario,
                "margen_unitario": margen_unitario,
                "margen_total": margen_total,
                "margen_pct": margen_pct,
                "movimientos_periodo": activity_row.get("movimientos", 0),
                "entradas_periodo": activity_row.get("entradas", 0),
                "salidas_periodo": activity_row.get("salidas", 0),
                "ajustes_periodo": activity_row.get("ajustes", 0),
                "balance_periodo": activity_row.get("balance", 0),
                "unidades_movidas": activity_row.get("unidades_movidas", 0),
                "ultima_actividad": activity_row.get("ultima_actividad"),
                "fecha_registro": producto.get("fecha_registro"),
                "ultima_actualizacion": producto.get("ultima_actualizacion"),
            }
            for campo in self._optional_fields():
                value = producto.get(campo["key"])
                row[campo["key"]] = _as_date(value) if campo["data_type"] == "date" else value
            rows.append(row)
        return rows

    def movement_rows(self):
        rows = []
        for movimiento in self.ctx["movimientos_filtrados"]:
            cantidad = _safe_int(movimiento.get("cantidad"))
            precio = _safe_float(movimiento.get("precio_unitario_producto"))
            tipo = str(movimiento.get("tipo_resuelto") or "").lower()
            factor = -1 if "salida" in tipo else 1
            fecha = movimiento.get("fecha_dt")
            rows.append(
                {
                    "registros": 1,
                    "id": movimiento.get("id"),
                    "fecha": fecha,
                    "fecha_dia": movimiento.get("fecha_date"),
                    "anio": fecha.year if fecha else None,
                    "mes": fecha.strftime("%Y-%m") if fecha else "",
                    "tipo_movimiento": movimiento.get("tipo_resuelto") or "Movimiento",
                    "cantidad": cantidad,
                    "cantidad_neta": cantidad * factor,
                    "valor_movimiento": cantidad * precio,
                    "valor_neto": cantidad * precio * factor,
                    "producto": movimiento.get("nombre_producto") or "Producto eliminado",
                    "codigo_producto": movimiento.get("codigo_producto") or "",
                    "categoria": movimiento.get("categoria_producto") or "General",
                    "proveedor": movimiento.get("proveedor_producto") or "Sin proveedor",
                    "usuario": movimiento.get("usuario_nombre") or "Sistema",
                    "usuario_nombre": movimiento.get("usuario_completo") or movimiento.get("usuario_nombre") or "Sistema",
                    "rol_usuario": movimiento.get("rol_usuario") or "Sistema",
                    "estado_producto": "Activo" if movimiento.get("producto_activo") else "Inactivo",
                    "stock_actual_producto": _safe_int(movimiento.get("stock_actual_producto")),
                    "stock_minimo_producto": _safe_int(movimiento.get("stock_minimo_producto")),
                    "precio_producto": precio,
                    "descripcion": movimiento.get("descripcion") or "",
                }
            )
        return rows

    def category_rows(self):
        actividad = defaultdict(
            lambda: {"movimientos": 0, "entradas": 0, "salidas": 0, "ajustes": 0, "balance": 0, "ultima_actividad": None}
        )
        for movimiento in self.ctx["movimientos_filtrados"]:
            categoria = movimiento.get("categoria_producto") or "General"
            row = actividad[categoria]
            tipo = str(movimiento.get("tipo_resuelto") or "").lower()
            cantidad = _safe_int(movimiento.get("cantidad"))
            row["movimientos"] += 1
            if "entrada" in tipo:
                row["entradas"] += cantidad
                row["balance"] += cantidad
            elif "salida" in tipo:
                row["salidas"] += cantidad
                row["balance"] -= cantidad
            else:
                row["ajustes"] += cantidad
            fecha = movimiento.get("fecha_dt")
            if fecha and (row["ultima_actividad"] is None or fecha > row["ultima_actividad"]):
                row["ultima_actividad"] = fecha

        rows_map = defaultdict(
            lambda: {
                "registros": 1,
                "categoria": "General",
                "productos": 0,
                "stock_total": 0,
                "stock_minimo_total": 0,
                "stock_maximo_total": 0,
                "productos_criticos": 0,
                "productos_sin_stock": 0,
                "valor_inventario": 0.0,
                "costo_inventario": 0.0,
                "margen_total": 0.0,
            }
        )
        for producto in self.ctx["productos_filtrados"]:
            categoria = producto.get("categoria_resuelta") or "General"
            row = rows_map[categoria]
            cantidad = _safe_int(producto.get("cantidad"))
            stock_minimo = _safe_int(producto.get("stock_minimo"), 5)
            stock_maximo = _safe_int(producto.get("stock_maximo"))
            row["categoria"] = categoria
            row["productos"] += 1
            row["stock_total"] += cantidad
            row["stock_minimo_total"] += stock_minimo
            row["stock_maximo_total"] += stock_maximo
            row["valor_inventario"] += cantidad * _safe_float(producto.get("precio_unitario"))
            row["costo_inventario"] += cantidad * _safe_float(producto.get("precio_compra"))
            row["margen_total"] = row["valor_inventario"] - row["costo_inventario"]
            if cantidad <= stock_minimo:
                row["productos_criticos"] += 1
            if cantidad == 0:
                row["productos_sin_stock"] += 1

        rows = []
        for categoria, row in rows_map.items():
            data = actividad.get(categoria) or {}
            rows.append(
                {
                    **row,
                    "movimientos": data.get("movimientos", 0),
                    "entradas": data.get("entradas", 0),
                    "salidas": data.get("salidas", 0),
                    "ajustes": data.get("ajustes", 0),
                    "balance": data.get("balance", 0),
                    "ultima_actividad": data.get("ultima_actividad"),
                }
            )
        rows.sort(key=lambda item: (_safe_float(item.get("valor_inventario")), item.get("categoria")), reverse=True)
        return rows

    def supplier_rows(self):
        actividad = defaultdict(
            lambda: {"movimientos": 0, "entradas": 0, "salidas": 0, "ajustes": 0, "unidades_movidas": 0, "ultima_actividad": None}
        )
        for movimiento in self.ctx["movimientos_filtrados"]:
            key = movimiento.get("id_proveedor") or movimiento.get("proveedor_producto") or "Sin proveedor"
            row = actividad[key]
            tipo = str(movimiento.get("tipo_resuelto") or "").lower()
            cantidad = _safe_int(movimiento.get("cantidad"))
            row["movimientos"] += 1
            row["unidades_movidas"] += cantidad
            if "entrada" in tipo:
                row["entradas"] += cantidad
            elif "salida" in tipo:
                row["salidas"] += cantidad
            else:
                row["ajustes"] += cantidad
            fecha = movimiento.get("fecha_dt")
            if fecha and (row["ultima_actividad"] is None or fecha > row["ultima_actividad"]):
                row["ultima_actividad"] = fecha

        rows_map = defaultdict(
            lambda: {
                "registros": 1,
                "proveedor": "Sin proveedor",
                "estado": "Activo",
                "ruc_nit": "",
                "telefono": "",
                "correo": "",
                "contacto": "",
                "productos": 0,
                "stock_total": 0,
                "valor_inventario": 0.0,
                "costo_inventario": 0.0,
                "productos_criticos": 0,
            }
        )
        for producto in self.ctx["productos_filtrados"]:
            key = producto.get("id_proveedor") or producto.get("proveedor_resuelto") or "Sin proveedor"
            info = self.ctx["proveedores_by_id"].get(producto.get("id_proveedor")) or {}
            row = rows_map[key]
            cantidad = _safe_int(producto.get("cantidad"))
            row["proveedor"] = producto.get("proveedor_resuelto") or "Sin proveedor"
            row["estado"] = "Activo" if bool(info.get("activo", 1)) else "Inactivo"
            row["ruc_nit"] = info.get("ruc_nit") or ""
            row["telefono"] = info.get("telefono") or ""
            row["correo"] = info.get("correo") or ""
            row["contacto"] = info.get("contacto") or ""
            row["productos"] += 1
            row["stock_total"] += cantidad
            row["valor_inventario"] += cantidad * _safe_float(producto.get("precio_unitario"))
            row["costo_inventario"] += cantidad * _safe_float(producto.get("precio_compra"))
            if cantidad <= _safe_int(producto.get("stock_minimo"), 5):
                row["productos_criticos"] += 1

        rows = []
        for key, row in rows_map.items():
            data = actividad.get(key) or {}
            rows.append(
                {
                    **row,
                    "movimientos": data.get("movimientos", 0),
                    "entradas": data.get("entradas", 0),
                    "salidas": data.get("salidas", 0),
                    "ajustes": data.get("ajustes", 0),
                    "unidades_movidas": data.get("unidades_movidas", 0),
                    "ultima_actividad": data.get("ultima_actividad"),
                }
            )
        rows.sort(key=lambda item: (_safe_float(item.get("valor_inventario")), item.get("proveedor")), reverse=True)
        return rows

    def user_rows(self):
        rows_map = defaultdict(
            lambda: {
                "registros": 1,
                "usuario": "sistema",
                "nombre": "Sistema",
                "rol": "Sistema",
                "estado": "Activo",
                "ultimo_login": None,
                "movimientos": 0,
                "entradas": 0,
                "salidas": 0,
                "ajustes": 0,
                "unidades_movidas": 0,
                "ultimo_movimiento": None,
            }
        )
        for usuario in self.ctx["usuarios"]:
            row = rows_map[usuario.get("id") or usuario.get("username")]
            row["usuario"] = usuario.get("username") or "sistema"
            row["nombre"] = usuario.get("nombre_completo") or usuario.get("username") or "Sistema"
            row["rol"] = usuario.get("rol") or "Sistema"
            row["estado"] = "Activo" if bool(usuario.get("activo", 1)) else "Inactivo"
            row["ultimo_login"] = usuario.get("ultimo_login")
        for movimiento in self.ctx["movimientos_filtrados"]:
            key = movimiento.get("id_usuario") or movimiento.get("usuario_nombre") or "sistema"
            row = rows_map[key]
            row["usuario"] = movimiento.get("usuario_nombre") or row["usuario"]
            row["nombre"] = movimiento.get("usuario_completo") or row["nombre"]
            row["rol"] = movimiento.get("rol_usuario") or row["rol"]
            row["movimientos"] += 1
            cantidad = _safe_int(movimiento.get("cantidad"))
            row["unidades_movidas"] += cantidad
            tipo = str(movimiento.get("tipo_resuelto") or "").lower()
            if "entrada" in tipo:
                row["entradas"] += cantidad
            elif "salida" in tipo:
                row["salidas"] += cantidad
            else:
                row["ajustes"] += cantidad
            fecha = movimiento.get("fecha_dt")
            if fecha and (row["ultimo_movimiento"] is None or fecha > row["ultimo_movimiento"]):
                row["ultimo_movimiento"] = fecha
        rows = list(rows_map.values())
        rows.sort(key=lambda item: (item.get("movimientos", 0), item.get("unidades_movidas", 0)), reverse=True)
        return rows

    def _choices_for_field(self, rows, field):
        if field["data_type"] not in {"text", "date", "datetime"}:
            return []
        values = []
        seen = set()
        for row in rows:
            value = row.get(field["key"])
            if value in (None, ""):
                continue
            text = value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            values.append(text)
            if len(values) > 40:
                return []
        return sorted(values)

    def source_definitions(self):
        sources = {
            "productos": {
                "label": "Productos",
                "description": "Inventario actual enriquecido con actividad del periodo filtrado.",
                "rows": self.product_rows(),
                "fields": [
                    self._field("registros", "Registros", "number", "number", chart_x=False),
                    self._field("id", "ID", "number", "number", chart_y=False),
                    self._field("codigo", "Codigo", "text", default_selected=True),
                    self._field("producto", "Producto", "text", default_selected=True),
                    self._field("descripcion", "Descripcion", "text", chart_x=False),
                    self._field("categoria", "Categoria", "text", default_selected=True),
                    self._field("proveedor", "Proveedor", "text", default_selected=True),
                    self._field("unidad", "Unidad", "text"),
                    self._field("estado", "Estado", "text"),
                    self._field("estado_stock", "Estado stock", "text"),
                    self._field("stock_actual", "Stock actual", "number", "number", default_selected=True),
                    self._field("stock_minimo", "Stock minimo", "number", "number"),
                    self._field("stock_maximo", "Stock maximo", "number", "number"),
                    self._field("precio_compra", "Precio compra", "currency", "currency"),
                    self._field("precio_venta", "Precio venta", "currency", "currency", default_selected=True),
                    self._field("valor_inventario", "Valor inventario", "currency", "currency", default_selected=True),
                    self._field("costo_inventario", "Costo inventario", "currency", "currency"),
                    self._field("margen_unitario", "Margen unitario", "currency", "currency"),
                    self._field("margen_total", "Margen total", "currency", "currency"),
                    self._field("margen_pct", "Margen %", "percent", "percent"),
                    self._field("movimientos_periodo", "Movimientos periodo", "number", "number"),
                    self._field("entradas_periodo", "Entradas periodo", "number", "number"),
                    self._field("salidas_periodo", "Salidas periodo", "number", "number"),
                    self._field("ajustes_periodo", "Ajustes periodo", "number", "number"),
                    self._field("balance_periodo", "Balance periodo", "number", "number"),
                    self._field("unidades_movidas", "Unidades movidas", "number", "number"),
                    self._field("ultima_actividad", "Ultima actividad", "datetime", "datetime"),
                    self._field("fecha_registro", "Fecha registro", "datetime", "datetime"),
                    self._field("ultima_actualizacion", "Ultima actualizacion", "datetime", "datetime"),
                ] + self._optional_fields(),
                "default_columns": ["codigo", "producto", "categoria", "proveedor", "stock_actual", "precio_venta", "valor_inventario"],
                "default_chart": {"x_field": "categoria", "y_field": "valor_inventario", "chart_type": "Barras verticales", "aggregation": "Suma", "limit": "Top 10"},
                "default_sort_field": "valor_inventario",
            },
            "movimientos": {
                "label": "Movimientos",
                "description": "Detalle operativo de entradas, salidas y ajustes dentro del periodo filtrado.",
                "rows": self.movement_rows(),
                "fields": [
                    self._field("registros", "Registros", "number", "number", chart_x=False),
                    self._field("id", "ID", "number", "number", chart_y=False),
                    self._field("fecha", "Fecha movimiento", "datetime", "datetime", default_selected=True),
                    self._field("fecha_dia", "Fecha", "date", "date"),
                    self._field("anio", "Anio", "number", "number", chart_y=False),
                    self._field("mes", "Mes", "text"),
                    self._field("tipo_movimiento", "Tipo movimiento", "text", default_selected=True),
                    self._field("producto", "Producto", "text", default_selected=True),
                    self._field("codigo_producto", "Codigo producto", "text"),
                    self._field("categoria", "Categoria", "text"),
                    self._field("proveedor", "Proveedor", "text"),
                    self._field("usuario", "Usuario", "text"),
                    self._field("usuario_nombre", "Nombre usuario", "text"),
                    self._field("rol_usuario", "Rol usuario", "text"),
                    self._field("estado_producto", "Estado producto", "text"),
                    self._field("cantidad", "Cantidad", "number", "number", default_selected=True),
                    self._field("cantidad_neta", "Cantidad neta", "number", "number"),
                    self._field("valor_movimiento", "Valor movimiento", "currency", "currency"),
                    self._field("valor_neto", "Valor neto", "currency", "currency"),
                    self._field("stock_actual_producto", "Stock actual producto", "number", "number"),
                    self._field("stock_minimo_producto", "Stock minimo producto", "number", "number"),
                    self._field("precio_producto", "Precio producto", "currency", "currency"),
                    self._field("descripcion", "Descripcion", "text", chart_x=False, default_selected=True),
                ],
                "default_columns": ["fecha", "tipo_movimiento", "producto", "cantidad", "usuario", "descripcion"],
                "default_chart": {"x_field": "fecha_dia", "y_field": "cantidad", "chart_type": "Linea", "aggregation": "Suma", "limit": "Ultimos 15"},
                "default_sort_field": "fecha",
            },
            "categorias": {
                "label": "Categorias",
                "description": "Resumen analitico por categoria usando el contexto filtrado actual.",
                "rows": self.category_rows(),
                "fields": [
                    self._field("registros", "Registros", "number", "number", chart_x=False),
                    self._field("categoria", "Categoria", "text", default_selected=True),
                    self._field("productos", "Productos", "number", "number", default_selected=True),
                    self._field("stock_total", "Stock total", "number", "number", default_selected=True),
                    self._field("stock_minimo_total", "Stock minimo total", "number", "number"),
                    self._field("stock_maximo_total", "Stock maximo total", "number", "number"),
                    self._field("productos_criticos", "Productos criticos", "number", "number"),
                    self._field("productos_sin_stock", "Productos sin stock", "number", "number"),
                    self._field("valor_inventario", "Valor inventario", "currency", "currency", default_selected=True),
                    self._field("costo_inventario", "Costo inventario", "currency", "currency"),
                    self._field("margen_total", "Margen total", "currency", "currency"),
                    self._field("movimientos", "Movimientos", "number", "number"),
                    self._field("entradas", "Entradas", "number", "number"),
                    self._field("salidas", "Salidas", "number", "number"),
                    self._field("ajustes", "Ajustes", "number", "number"),
                    self._field("balance", "Balance", "number", "number"),
                    self._field("ultima_actividad", "Ultima actividad", "datetime", "datetime"),
                ],
                "default_columns": ["categoria", "productos", "stock_total", "valor_inventario", "movimientos", "balance"],
                "default_chart": {"x_field": "categoria", "y_field": "valor_inventario", "chart_type": "Pastel", "aggregation": "Suma", "limit": "Top 10"},
                "default_sort_field": "valor_inventario",
            },
            "proveedores": {
                "label": "Proveedores",
                "description": "Consolidado de inventario y actividad por proveedor.",
                "rows": self.supplier_rows(),
                "fields": [
                    self._field("registros", "Registros", "number", "number", chart_x=False),
                    self._field("proveedor", "Proveedor", "text", default_selected=True),
                    self._field("estado", "Estado", "text"),
                    self._field("ruc_nit", "RUC/NIT", "text"),
                    self._field("telefono", "Telefono", "text"),
                    self._field("correo", "Correo", "text"),
                    self._field("contacto", "Contacto", "text"),
                    self._field("productos", "Productos", "number", "number", default_selected=True),
                    self._field("stock_total", "Stock total", "number", "number", default_selected=True),
                    self._field("valor_inventario", "Valor inventario", "currency", "currency", default_selected=True),
                    self._field("costo_inventario", "Costo inventario", "currency", "currency"),
                    self._field("productos_criticos", "Productos criticos", "number", "number"),
                    self._field("movimientos", "Movimientos", "number", "number"),
                    self._field("entradas", "Entradas", "number", "number"),
                    self._field("salidas", "Salidas", "number", "number"),
                    self._field("ajustes", "Ajustes", "number", "number"),
                    self._field("unidades_movidas", "Unidades movidas", "number", "number"),
                    self._field("ultima_actividad", "Ultima actividad", "datetime", "datetime"),
                ],
                "default_columns": ["proveedor", "productos", "stock_total", "valor_inventario", "productos_criticos", "movimientos"],
                "default_chart": {"x_field": "proveedor", "y_field": "valor_inventario", "chart_type": "Barras horizontales", "aggregation": "Suma", "limit": "Top 10"},
                "default_sort_field": "valor_inventario",
            },
            "usuarios": {
                "label": "Usuarios",
                "description": "Actividad operativa y trazabilidad por usuario del sistema.",
                "rows": self.user_rows(),
                "fields": [
                    self._field("registros", "Registros", "number", "number", chart_x=False),
                    self._field("usuario", "Usuario", "text", default_selected=True),
                    self._field("nombre", "Nombre", "text", default_selected=True),
                    self._field("rol", "Rol", "text", default_selected=True),
                    self._field("estado", "Estado", "text"),
                    self._field("ultimo_login", "Ultimo login", "datetime", "datetime"),
                    self._field("movimientos", "Movimientos", "number", "number", default_selected=True),
                    self._field("entradas", "Entradas", "number", "number"),
                    self._field("salidas", "Salidas", "number", "number"),
                    self._field("ajustes", "Ajustes", "number", "number"),
                    self._field("unidades_movidas", "Unidades movidas", "number", "number", default_selected=True),
                    self._field("ultimo_movimiento", "Ultimo movimiento", "datetime", "datetime"),
                ],
                "default_columns": ["usuario", "nombre", "rol", "movimientos", "unidades_movidas", "ultimo_movimiento"],
                "default_chart": {"x_field": "usuario", "y_field": "movimientos", "chart_type": "Barras verticales", "aggregation": "Suma", "limit": "Top 10"},
                "default_sort_field": "movimientos",
            },
        }
        for source in sources.values():
            source["fields_by_key"] = {field["key"]: field for field in source["fields"]}
            for field in source["fields"]:
                field["choices"] = self._choices_for_field(source["rows"], field)
        return sources

    def _field_value(self, row, field):
        value = row.get(field["key"])
        if field["data_type"] == "date":
            return _as_date(value)
        if field["data_type"] == "datetime":
            return _as_datetime(value)
        return value

    def _filter_match(self, value, operator, target, field):
        if operator == "Vacio":
            return value in (None, "")
        if operator == "Con valor":
            return value not in (None, "")
        if field["data_type"] in {"number", "currency", "percent"}:
            current = _safe_float(value)
            target_value = _safe_float(target)
            return {
                "=": current == target_value,
                "!=": current != target_value,
                ">": current > target_value,
                ">=": current >= target_value,
                "<": current < target_value,
                "<=": current <= target_value,
            }.get(operator, False)
        if field["data_type"] in {"date", "datetime"}:
            current = _as_datetime(value)
            target_value = _as_datetime(target)
            if not current or not target_value:
                return False
            return {
                "=": current == target_value,
                ">": current > target_value,
                ">=": current >= target_value,
                "<": current < target_value,
                "<=": current <= target_value,
            }.get(operator, False)
        current = str(value or "").strip().lower()
        target_text = str(target or "").strip().lower()
        return {
            "Es": current == target_text,
            "No es": current != target_text,
            "Contiene": target_text in current,
            "Empieza con": current.startswith(target_text),
            "Termina con": current.endswith(target_text),
        }.get(operator, False)

    def apply_extra_filters(self, rows, fields_by_key, filters):
        output = list(rows or [])
        for item in filters or []:
            field = fields_by_key.get(item.get("field"))
            operator = item.get("operator")
            if not field or not operator:
                continue
            output = [
                row
                for row in output
                if self._filter_match(self._field_value(row, field), operator, item.get("value"), field)
            ]
        return output

    def sort_rows(self, rows, field_key, direction, fields_by_key):
        if not field_key or field_key not in fields_by_key:
            return list(rows or [])
        field = fields_by_key[field_key]
        reverse = str(direction or "desc").lower() == "desc"

        def _sort_key(row):
            value = self._field_value(row, field)
            if field["data_type"] in {"number", "currency", "percent"}:
                return (value is None, _safe_float(value))
            if field["data_type"] in {"date", "datetime"}:
                return (value is None, value or datetime.min)
            return (value in (None, ""), str(value or "").lower())

        return sorted(rows or [], key=_sort_key, reverse=reverse)

    def export_filters_summary(self, source, extra_filters=None, extra_pairs=None):
        summary = {"Origen": source["label"]}
        for item in self.owner._contexto_dashboard_reportes(self.filtros_base, self.ctx):
            summary[item.get("label") or "Filtro"] = item.get("value") or "-"
        if extra_filters:
            summary["Filtros avanzados"] = " | ".join(extra_filters)
        for key, value in extra_pairs or []:
            if value not in (None, "", []):
                summary[key] = value
        return summary

    def catalog(self):
        sources = self.source_definitions()
        return {
            "sources": {
                key: {
                    "key": key,
                    "label": source["label"],
                    "description": source["description"],
                    "row_count": len(source["rows"]),
                    "fields": [
                        {
                            "key": field["key"],
                            "label": field["label"],
                            "data_type": field["data_type"],
                            "format": field.get("format"),
                            "chart_x": field.get("chart_x"),
                            "chart_y": field.get("chart_y"),
                            "default_selected": field.get("default_selected"),
                            "filter_ops": list(field.get("filter_ops") or []),
                            "choices": list(field.get("choices") or []),
                        }
                        for field in source["fields"]
                    ],
                    "default_columns": list(source.get("default_columns") or []),
                    "default_chart": dict(source.get("default_chart") or {}),
                    "default_sort_field": source.get("default_sort_field"),
                }
                for key, source in sources.items()
            }
        }

    def build_chart(self, config):
        sources = self.source_definitions()
        source_key = str((config or {}).get("source") or "").strip()
        source = sources.get(source_key)
        if not source:
            raise ValueError("Selecciona una fuente valida para generar el grafico.")

        fields_by_key = source["fields_by_key"]
        x_field = str((config or {}).get("x_field") or "").strip()
        y_field = str((config or {}).get("y_field") or "").strip()
        chart_type = str((config or {}).get("chart_type") or "Barras verticales").strip()
        aggregation = str((config or {}).get("aggregation") or "Suma").strip()
        limit = str((config or {}).get("limit") or "Top 10").strip()
        extra_filters = list((config or {}).get("extra_filters") or [])

        if x_field not in fields_by_key:
            raise ValueError("Selecciona un campo para el eje X.")
        if y_field not in fields_by_key:
            raise ValueError("Selecciona un campo para el eje Y.")
        if aggregation not in self.AGGREGATIONS:
            raise ValueError("Selecciona una agregacion valida.")

        x_meta = fields_by_key[x_field]
        y_meta = fields_by_key[y_field]
        if not x_meta.get("chart_x"):
            raise ValueError(f"El campo '{x_meta['label']}' no es adecuado para el eje X.")
        if not y_meta.get("chart_y"):
            raise ValueError(f"El campo '{y_meta['label']}' no contiene valores numericos para el eje Y.")

        rows = self.apply_extra_filters(source["rows"], fields_by_key, extra_filters)
        if not rows:
            raise ValueError("No hay datos disponibles con los filtros seleccionados.")

        buckets = {}
        for row in rows:
            x_value = self._field_value(row, x_meta)
            x_key = x_value if x_value not in (None, "") else "Sin dato"
            bucket = buckets.setdefault(
                x_key,
                {
                    "x_raw": x_value,
                    "x_label": x_value.strftime("%Y-%m-%d") if hasattr(x_value, "strftime") else str(x_key),
                    "values": [],
                    "registros": 0,
                },
            )
            bucket["values"].append(_safe_float(self._field_value(row, y_meta)))
            bucket["registros"] += 1

        def _agg(values):
            if aggregation == "Promedio":
                return sum(values) / len(values) if values else 0.0
            if aggregation == "Maximo":
                return max(values) if values else 0.0
            if aggregation == "Minimo":
                return min(values) if values else 0.0
            return sum(values)

        series = [
            {
                "x_raw": bucket["x_raw"],
                "x_label": bucket["x_label"],
                "value": _agg(bucket["values"]),
                "registros": bucket["registros"],
            }
            for bucket in buckets.values()
        ]

        if chart_type in {"Linea", "Area"}:
            if x_meta["data_type"] in {"date", "datetime"}:
                series.sort(key=lambda item: item.get("x_raw") or datetime.min)
            elif x_meta["data_type"] in {"number", "currency", "percent"}:
                series.sort(key=lambda item: _safe_float(item.get("x_raw")))
            else:
                series.sort(key=lambda item: str(item.get("x_label") or "").lower())
        else:
            series.sort(key=lambda item: _safe_float(item.get("value")), reverse=True)

        top_map = {"Top 5": 5, "Top 10": 10, "Top 15": 15, "Top 20": 20}
        if limit.startswith("Ultimos "):
            try:
                count = int("".join(ch for ch in limit if ch.isdigit()))
            except ValueError:
                count = 15
            series = series[-count:]
        elif limit in top_map:
            series = series[: top_map[limit]]

        if chart_type in {"Pastel", "Dona"}:
            series = [item for item in series if _safe_float(item.get("value")) > 0]
            if not series:
                raise ValueError("Los graficos circulares necesitan valores positivos en el eje Y.")

        filters_text = []
        for item in extra_filters:
            field = fields_by_key.get(item.get("field")) or {}
            filters_text.append(f"{field.get('label') or item.get('field')}: {item.get('operator')} {item.get('value')}")

        return {
            "source_key": source_key,
            "source_label": source["label"],
            "chart_type": chart_type,
            "x_label": x_meta["label"],
            "y_label": f"{aggregation} de {y_meta['label']}",
            "y_format": y_meta.get("format") or "number",
            "series": series,
            "summary": {
                "Filas analizadas": len(rows),
                "Puntos visibles": len(series),
                "Total eje Y": sum(_safe_float(item.get("value")) for item in series),
            },
            "preview_columns": ["Dimension", "Valor", "Registros"],
            "preview_rows": [{"Dimension": item["x_label"], "Valor": item["value"], "Registros": item["registros"]} for item in series],
            "preview_formats": {"Valor": y_meta.get("format") or "number", "Registros": "number"},
            "title": f"{source['label']} por {x_meta['label']}",
            "subtitle": f"{chart_type} con {aggregation.lower()} de {y_meta['label'].lower()}.",
            "filters_export": self.export_filters_summary(
                source,
                extra_filters=filters_text,
                extra_pairs=[("Eje X", x_meta["label"]), ("Eje Y", y_meta["label"]), ("Agregacion", aggregation), ("Grafico", chart_type)],
            ),
        }

    def build_report(self, config):
        sources = self.source_definitions()
        source_key = str((config or {}).get("source") or "").strip()
        source = sources.get(source_key)
        if not source:
            raise ValueError("Selecciona una fuente valida para construir el reporte.")

        fields_by_key = source["fields_by_key"]
        columns = [col for col in (config or {}).get("columns") or [] if col in fields_by_key]
        if not columns:
            raise ValueError("Selecciona al menos una columna para el reporte personalizado.")

        sort_field = str((config or {}).get("sort_field") or "").strip() or source.get("default_sort_field")
        sort_direction = str((config or {}).get("sort_direction") or "desc").strip().lower()
        include_summary = bool((config or {}).get("include_summary", True))
        include_totals = bool((config or {}).get("include_totals"))
        include_subtotals = bool((config or {}).get("include_subtotals"))
        subtotal_field = str((config or {}).get("subtotal_field") or "").strip()
        extra_filters = list((config or {}).get("extra_filters") or [])

        rows = self.apply_extra_filters(source["rows"], fields_by_key, extra_filters)
        rows = self.sort_rows(rows, sort_field, sort_direction, fields_by_key)

        labels = [fields_by_key[col]["label"] for col in columns]
        formats = {fields_by_key[col]["label"]: fields_by_key[col].get("format") for col in columns if fields_by_key[col].get("format")}
        numeric_cols = [col for col in columns if fields_by_key[col]["data_type"] in {"number", "currency", "percent"}]

        def _render_row(raw_row):
            return {fields_by_key[col]["label"]: self._field_value(raw_row, fields_by_key[col]) for col in columns}

        rendered_rows = [_render_row(row) for row in rows]

        if include_subtotals and subtotal_field in fields_by_key and rows:
            grouped_rows = []
            current_group = None
            totals = {col: 0.0 for col in numeric_cols}
            for raw_row in rows:
                group_value = str(self._field_value(raw_row, fields_by_key[subtotal_field]) or "Sin dato")
                if current_group is None:
                    current_group = group_value
                if group_value != current_group:
                    subtotal_row = {label: "" for label in labels}
                    subtotal_row[labels[0]] = f"Subtotal - {current_group}"
                    for col in numeric_cols:
                        subtotal_row[fields_by_key[col]["label"]] = totals[col]
                    grouped_rows.append(subtotal_row)
                    totals = {col: 0.0 for col in numeric_cols}
                    current_group = group_value
                grouped_rows.append(_render_row(raw_row))
                for col in numeric_cols:
                    totals[col] += _safe_float(self._field_value(raw_row, fields_by_key[col]))
            subtotal_row = {label: "" for label in labels}
            subtotal_row[labels[0]] = f"Subtotal - {current_group}"
            for col in numeric_cols:
                subtotal_row[fields_by_key[col]["label"]] = totals[col]
            grouped_rows.append(subtotal_row)
            rendered_rows = grouped_rows

        if include_totals and numeric_cols:
            total_row = {label: "" for label in labels}
            total_row[labels[0]] = "TOTAL GENERAL"
            for col in numeric_cols:
                total_row[fields_by_key[col]["label"]] = sum(_safe_float(self._field_value(row, fields_by_key[col])) for row in rows)
            rendered_rows.append(total_row)

        summary = {}
        if include_summary:
            summary["Fuente"] = source["label"]
            summary["Registros base"] = len(rows)
            summary["Columnas visibles"] = len(columns)
            if sort_field in fields_by_key:
                summary["Ordenado por"] = f"{fields_by_key[sort_field]['label']} ({'DESC' if sort_direction == 'desc' else 'ASC'})"
            for col in numeric_cols[:4]:
                summary[f"Total {fields_by_key[col]['label']}"] = sum(_safe_float(self._field_value(row, fields_by_key[col])) for row in rows)

        filters_text = []
        for item in extra_filters:
            field = fields_by_key.get(item.get("field")) or {}
            filters_text.append(f"{field.get('label') or item.get('field')}: {item.get('operator')} {item.get('value')}")

        report = self.owner._base_reporte(
            "reporte_personalizado",
            f"Reporte personalizado - {source['label']}",
            source["description"],
            labels,
            rendered_rows,
            formatos=formats,
            resumen=summary,
        )
        report["source_key"] = source_key
        report["selected_columns"] = list(columns)
        report["filters_export"] = self.export_filters_summary(
            source,
            extra_filters=filters_text,
            extra_pairs=[
                ("Columnas", ", ".join(labels)),
                ("Subtotales", fields_by_key[subtotal_field]["label"] if include_subtotals and subtotal_field in fields_by_key else "No"),
            ],
        )
        return report
