import json
from collections import defaultdict
from datetime import datetime, timedelta

from mysql.connector import Error
from .reportes_dynamic import DynamicReportsService


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
        return datetime(value.year, value.month, value.day)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return None


def _as_date(value):
    dt = _as_datetime(value)
    return dt.date() if dt else None


def _slug(texto):
    limpio = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(texto or "reporte"))
    while "__" in limpio:
        limpio = limpio.replace("__", "_")
    return limpio.strip("_") or "reporte"


class ReportesMixin:
    """
    Construye reportes avanzados reutilizando el modelo existente del sistema.

    La UI y los exportadores consumen una sola estructura para evitar duplicar
    reglas de negocio entre pantalla, PDF y Excel.
    """

    ESTADOS_VALIDOS = {"activos", "inactivos", "stock_bajo", "sin_stock", "todos"}

    def obtener_fuentes_reportes(self):
        try:
            productos = [dict(p) for p in self.obtener_productos(solo_activos=False)]
            proveedores = sorted(
                [dict(p) for p in self.obtener_proveedores()],
                key=lambda item: str(item.get("nombre") or "").lower(),
            )
            usuarios = sorted(
                [dict(u) for u in self.obtener_usuarios()],
                key=lambda item: str(item.get("username") or "").lower(),
            )
            categorias = set(self.obtener_nombres_categorias())
            categorias.update((p.get("categoria") or "General") for p in productos)
            return {
                "categorias": sorted(c for c in categorias if c),
                "productos": sorted(productos, key=lambda item: str(item.get("nombre") or "").lower()),
                "proveedores": proveedores,
                "usuarios": usuarios,
            }
        except Exception as exc:
            print(f"[WARN] fuentes reportes: {exc}")
            return {"categorias": [], "productos": [], "proveedores": [], "usuarios": []}

    def _normalizar_filtros_reportes(self, filtros=None):
        filtros = dict(filtros or {})

        def _clean_text(key):
            valor = str(filtros.get(key) or "").strip()
            return "" if valor.lower() in {"todos", "todas", "all"} else valor

        def _clean_id(key):
            valor = filtros.get(key)
            if valor in (None, "", "Todos", "Todas"):
                return None
            try:
                return int(valor)
            except (TypeError, ValueError):
                return None

        estado = str(filtros.get("estado_producto") or "activos").strip().lower()
        mapa_estados = {
            "activo": "activos",
            "activos": "activos",
            "inactivo": "inactivos",
            "inactivos": "inactivos",
            "stock bajo": "stock_bajo",
            "stock_bajo": "stock_bajo",
            "stock-bajo": "stock_bajo",
            "sin stock": "sin_stock",
            "sin_stock": "sin_stock",
            "sin-stock": "sin_stock",
            "todos": "todos",
        }
        estado = mapa_estados.get(estado, "activos")
        if estado not in self.ESTADOS_VALIDOS:
            estado = "activos"

        return {
            "fecha_inicio": str(filtros.get("fecha_inicio") or "").strip(),
            "fecha_fin": str(filtros.get("fecha_fin") or "").strip(),
            "categoria": _clean_text("categoria"),
            "id_proveedor": _clean_id("id_proveedor"),
            "id_producto": _clean_id("id_producto"),
            "tipo_movimiento": _clean_text("tipo_movimiento"),
            "id_usuario": _clean_id("id_usuario"),
            "estado_producto": estado,
        }

    def _estado_producto_match(self, producto, estado):
        activo = bool(producto.get("activo", 1))
        cantidad = _safe_int(producto.get("cantidad"))
        stock_minimo = _safe_int(producto.get("stock_minimo"), 5)

        if estado == "inactivos":
            return not activo
        if estado == "stock_bajo":
            return activo and cantidad <= stock_minimo
        if estado == "sin_stock":
            return activo and cantidad == 0
        if estado == "todos":
            return True
        return activo

    def _filtrar_productos_reportes(self, productos, filtros):
        resultado = []
        for producto in productos:
            if filtros.get("categoria") and (producto.get("categoria_resuelta") or "") != filtros["categoria"]:
                continue
            if filtros.get("id_proveedor") and producto.get("id_proveedor") != filtros["id_proveedor"]:
                continue
            if filtros.get("id_producto") and producto.get("id") != filtros["id_producto"]:
                continue
            if not self._estado_producto_match(producto, filtros.get("estado_producto") or "activos"):
                continue
            resultado.append(producto)
        return resultado

    def _filtrar_movimientos_reportes(self, movimientos, filtros):
        fecha_inicio = _as_date(filtros.get("fecha_inicio"))
        fecha_fin = _as_date(filtros.get("fecha_fin"))
        tipo_movimiento = str(filtros.get("tipo_movimiento") or "").strip().lower()
        resultado = []

        for movimiento in movimientos:
            fecha = movimiento.get("fecha_date")
            if fecha_inicio and (not fecha or fecha < fecha_inicio):
                continue
            if fecha_fin and (not fecha or fecha > fecha_fin):
                continue
            if filtros.get("categoria") and (movimiento.get("categoria_producto") or "") != filtros["categoria"]:
                continue
            if filtros.get("id_proveedor") and movimiento.get("id_proveedor") != filtros["id_proveedor"]:
                continue
            if filtros.get("id_producto") and movimiento.get("id_producto") != filtros["id_producto"]:
                continue
            if filtros.get("id_usuario") and movimiento.get("id_usuario") != filtros["id_usuario"]:
                continue
            if tipo_movimiento and str(movimiento.get("tipo_resuelto") or "").lower() != tipo_movimiento:
                continue

            producto_stub = {
                "activo": 1 if movimiento.get("producto_activo") else 0,
                "cantidad": movimiento.get("stock_actual_producto"),
                "stock_minimo": movimiento.get("stock_minimo_producto"),
            }
            if not self._estado_producto_match(producto_stub, filtros.get("estado_producto") or "activos"):
                continue
            resultado.append(movimiento)
        return resultado

    def _snapshot_reportes(self, filtros):
        # Construimos un snapshot enriquecido para que todos los reportes
        # trabajen sobre la misma foto de datos y no repitan joins o lookups.
        productos = [dict(p) for p in self.obtener_productos(solo_activos=False)]
        proveedores = [dict(p) for p in self.obtener_proveedores()]
        usuarios = [dict(u) for u in self.obtener_usuarios()]
        movimientos_raw = [dict(m) for m in self.obtener_movimientos()]

        proveedores_by_id = {p["id"]: p for p in proveedores}
        usuarios_by_id = {u["id"]: u for u in usuarios}
        productos_by_id = {}

        for producto in productos:
            proveedor = proveedores_by_id.get(producto.get("id_proveedor")) or {}
            producto["categoria_resuelta"] = producto.get("categoria") or "General"
            producto["proveedor_resuelto"] = (
                producto.get("proveedor")
                or proveedor.get("nombre")
                or "Sin proveedor"
            )
            producto["unidad_resuelta"] = producto.get("unidad_medida") or "Unidad"
            productos_by_id[producto["id"]] = producto

        movimientos = []
        for movimiento in movimientos_raw:
            producto = productos_by_id.get(movimiento.get("id_producto")) or {}
            usuario = usuarios_by_id.get(movimiento.get("id_usuario")) or {}
            fecha_dt = _as_datetime(movimiento.get("fecha"))
            tipo_resuelto = str(movimiento.get("tipo_movimiento") or "").strip().title() or "Movimiento"
            enriquecido = dict(movimiento)
            enriquecido["fecha_dt"] = fecha_dt
            enriquecido["fecha_date"] = fecha_dt.date() if fecha_dt else None
            enriquecido["tipo_resuelto"] = tipo_resuelto
            enriquecido["nombre_producto"] = producto.get("nombre") or "Producto eliminado"
            enriquecido["codigo_producto"] = producto.get("codigo") or ""
            enriquecido["categoria_producto"] = producto.get("categoria_resuelta") or "General"
            enriquecido["id_proveedor"] = producto.get("id_proveedor")
            enriquecido["proveedor_producto"] = producto.get("proveedor_resuelto") or "Sin proveedor"
            enriquecido["producto_activo"] = bool(producto.get("activo", 0))
            enriquecido["stock_actual_producto"] = _safe_int(producto.get("cantidad"))
            enriquecido["stock_minimo_producto"] = _safe_int(producto.get("stock_minimo"), 5)
            enriquecido["precio_unitario_producto"] = _safe_float(producto.get("precio_unitario"))
            enriquecido["precio_compra_producto"] = _safe_float(producto.get("precio_compra"))
            enriquecido["usuario_nombre"] = usuario.get("username") or "Sistema"
            enriquecido["usuario_completo"] = (
                usuario.get("nombre_completo")
                or usuario.get("username")
                or "Sistema"
            )
            enriquecido["rol_usuario"] = usuario.get("rol") or "Sistema"
            movimientos.append(enriquecido)

        return {
            "productos": productos,
            "productos_filtrados": self._filtrar_productos_reportes(productos, filtros),
            "productos_by_id": productos_by_id,
            "proveedores": proveedores,
            "proveedores_by_id": proveedores_by_id,
            "usuarios": usuarios,
            "usuarios_by_id": usuarios_by_id,
            "movimientos": movimientos,
            "movimientos_filtrados": self._filtrar_movimientos_reportes(movimientos, filtros),
        }

    def _construir_dashboard_reportes(self, filtros, ctx):
        # El dashboard reutiliza el mismo contexto filtrado del reporte para
        # que KPIs, graficos y tabla previa siempre queden sincronizados.
        productos = ctx["productos_filtrados"]
        movimientos = ctx["movimientos_filtrados"]

        total_productos = len(productos)
        total_categorias = len({p.get("categoria_resuelta") or "General" for p in productos})
        if total_categorias == 0 and not filtros.get("categoria"):
            total_categorias = len(self.obtener_fuentes_reportes().get("categorias", []))

        proveedores_unicos = {
            p.get("id_proveedor") or p.get("proveedor_resuelto")
            for p in productos
            if p.get("id_proveedor") or p.get("proveedor_resuelto")
        }
        total_proveedores = len(proveedores_unicos)
        if total_proveedores == 0 and not filtros.get("id_proveedor"):
            total_proveedores = len(ctx["proveedores"])

        productos_stock_bajo = sum(
            1
            for p in productos
            if bool(p.get("activo", 1))
            and _safe_int(p.get("cantidad")) <= _safe_int(p.get("stock_minimo"), 5)
        )
        valor_total_inventario = sum(
            _safe_int(p.get("cantidad")) * _safe_float(p.get("precio_unitario"))
            for p in productos
        )
        costo_total_inventario = sum(
            _safe_int(p.get("cantidad")) * _safe_float(p.get("precio_compra"))
            for p in productos
        )

        entradas_periodo = sum(
            _safe_int(m.get("cantidad"))
            for m in movimientos
            if "entrada" in str(m.get("tipo_resuelto") or "").lower()
        )
        salidas_periodo = sum(
            _safe_int(m.get("cantidad"))
            for m in movimientos
            if "salida" in str(m.get("tipo_resuelto") or "").lower()
        )

        categorias = defaultdict(lambda: {"productos": 0, "stock_total": 0, "valor_total": 0.0})
        for producto in productos:
            categoria = producto.get("categoria_resuelta") or "General"
            cantidad = _safe_int(producto.get("cantidad"))
            valor = cantidad * _safe_float(producto.get("precio_unitario"))
            categorias[categoria]["productos"] += 1
            categorias[categoria]["stock_total"] += cantidad
            categorias[categoria]["valor_total"] += valor

        categorias_chart = [
            {
                "categoria": categoria,
                "productos": data["productos"],
                "stock_total": data["stock_total"],
                "valor_total": data["valor_total"],
            }
            for categoria, data in sorted(
                categorias.items(),
                key=lambda item: item[1]["valor_total"],
                reverse=True,
            )
        ]

        movimientos_por_fecha = defaultdict(lambda: {"entradas": 0, "salidas": 0, "movimientos": 0})
        for movimiento in movimientos:
            fecha = movimiento.get("fecha_date")
            if not fecha:
                continue
            tipo = str(movimiento.get("tipo_resuelto") or "").lower()
            movimientos_por_fecha[fecha]["movimientos"] += 1
            if "entrada" in tipo:
                movimientos_por_fecha[fecha]["entradas"] += _safe_int(movimiento.get("cantidad"))
            elif "salida" in tipo:
                movimientos_por_fecha[fecha]["salidas"] += _safe_int(movimiento.get("cantidad"))

        movimientos_chart = [
            {
                "fecha": fecha,
                "entradas": data["entradas"],
                "salidas": data["salidas"],
                "balance": data["entradas"] - data["salidas"],
                "movimientos": data["movimientos"],
            }
            for fecha, data in sorted(movimientos_por_fecha.items())
        ]
        if len(movimientos_chart) > 30:
            movimientos_chart = movimientos_chart[-30:]

        actividad_por_producto = defaultdict(
            lambda: {"unidades_movidas": 0, "movimientos": 0, "ultima_fecha": None}
        )
        for movimiento in movimientos:
            pid = movimiento.get("id_producto")
            actividad = actividad_por_producto[pid]
            actividad["unidades_movidas"] += _safe_int(movimiento.get("cantidad"))
            actividad["movimientos"] += 1
            fecha = movimiento.get("fecha_dt")
            if fecha and (actividad["ultima_fecha"] is None or fecha > actividad["ultima_fecha"]):
                actividad["ultima_fecha"] = fecha

        productos_chart = []
        for producto in productos:
            pid = producto.get("id")
            actividad = actividad_por_producto.get(pid) or {}
            cantidad = _safe_int(producto.get("cantidad"))
            valor = cantidad * _safe_float(producto.get("precio_unitario"))
            productos_chart.append(
                {
                    "id": pid,
                    "producto": producto.get("nombre") or f"Producto {pid}",
                    "categoria": producto.get("categoria_resuelta") or "General",
                    "proveedor": producto.get("proveedor_resuelto") or "Sin proveedor",
                    "stock_actual": cantidad,
                    "valor_inventario": valor,
                    "movimientos": actividad.get("movimientos", 0),
                    "unidades_movidas": actividad.get("unidades_movidas", 0),
                    "ultima_actividad": actividad.get("ultima_fecha"),
                }
            )

        top_productos_chart = [
            {
                "producto": item["producto"],
                "unidades": item["unidades_movidas"],
                "movimientos": item["movimientos"],
                "stock_actual": item["stock_actual"],
                "valor_inventario": item["valor_inventario"],
            }
            for item in sorted(
                productos_chart,
                key=lambda item: (item["unidades_movidas"], item["movimientos"]),
                reverse=True,
            )[:10]
        ]

        proveedores_chart_map = defaultdict(
            lambda: {
                "proveedor": "Sin proveedor",
                "productos": 0,
                "stock_total": 0,
                "valor_total": 0.0,
                "productos_criticos": 0,
            }
        )
        for producto in productos:
            key = producto.get("id_proveedor") or producto.get("proveedor_resuelto") or "Sin proveedor"
            fila = proveedores_chart_map[key]
            fila["proveedor"] = producto.get("proveedor_resuelto") or "Sin proveedor"
            fila["productos"] += 1
            cantidad = _safe_int(producto.get("cantidad"))
            fila["stock_total"] += cantidad
            fila["valor_total"] += cantidad * _safe_float(producto.get("precio_unitario"))
            if cantidad <= _safe_int(producto.get("stock_minimo"), 5):
                fila["productos_criticos"] += 1

        proveedores_chart = sorted(
            proveedores_chart_map.values(),
            key=lambda item: (item["valor_total"], item["productos"]),
            reverse=True,
        )

        return {
            "kpis": {
                "total_productos": total_productos,
                "total_categorias": total_categorias,
                "total_proveedores": total_proveedores,
                "productos_stock_bajo": productos_stock_bajo,
                "valor_total_inventario": valor_total_inventario,
                "costo_total_inventario": costo_total_inventario,
                "entradas_periodo": entradas_periodo,
                "salidas_periodo": salidas_periodo,
            },
            "contexto": self._contexto_dashboard_reportes(filtros, ctx),
            "categorias": categorias_chart[:10],
            "distribucion": categorias_chart[:8],
            "movimientos_fecha": movimientos_chart,
            "top_productos": top_productos_chart,
            "proveedores": proveedores_chart[:10],
            "datasets": {
                "categorias": categorias_chart,
                "productos": productos_chart,
                "proveedores": proveedores_chart,
                "movimientos_fecha": movimientos_chart,
            },
        }

    def _resumen_periodo(self, movimientos):
        entradas_unidades = 0
        salidas_unidades = 0
        valor_entradas = 0.0
        valor_salidas = 0.0
        productos = set()

        for movimiento in movimientos:
            cantidad = _safe_int(movimiento.get("cantidad"))
            precio = _safe_float(movimiento.get("precio_unitario_producto"))
            tipo = str(movimiento.get("tipo_resuelto") or "").lower()
            productos.add(movimiento.get("id_producto"))
            if "entrada" in tipo:
                entradas_unidades += cantidad
                valor_entradas += cantidad * precio
            elif "salida" in tipo:
                salidas_unidades += cantidad
                valor_salidas += cantidad * precio

        return {
            "entradas_unidades": entradas_unidades,
            "salidas_unidades": salidas_unidades,
            "balance_unidades": entradas_unidades - salidas_unidades,
            "total_movimientos": len(movimientos),
            "productos_con_movimiento": len(productos),
            "valor_entradas": valor_entradas,
            "valor_salidas": valor_salidas,
        }

    def _contexto_dashboard_reportes(self, filtros, ctx):
        contexto = []

        fecha_inicio = filtros.get("fecha_inicio")
        fecha_fin = filtros.get("fecha_fin")
        if fecha_inicio or fecha_fin:
            contexto.append(
                {
                    "label": "Periodo",
                    "value": f"{fecha_inicio or 'Inicio'} al {fecha_fin or 'Hoy'}",
                }
            )

        if filtros.get("categoria"):
            contexto.append({"label": "Categoria", "value": filtros["categoria"]})

        if filtros.get("id_proveedor"):
            proveedor = ctx["proveedores_by_id"].get(filtros["id_proveedor"]) or {}
            contexto.append(
                {
                    "label": "Proveedor",
                    "value": proveedor.get("nombre") or f"#{filtros['id_proveedor']}",
                }
            )

        if filtros.get("id_producto"):
            producto = ctx["productos_by_id"].get(filtros["id_producto"]) or {}
            contexto.append(
                {
                    "label": "Producto",
                    "value": producto.get("nombre") or f"#{filtros['id_producto']}",
                }
            )

        if filtros.get("tipo_movimiento"):
            contexto.append({"label": "Movimiento", "value": filtros["tipo_movimiento"].title()})

        if filtros.get("id_usuario"):
            usuario = ctx["usuarios_by_id"].get(filtros["id_usuario"]) or {}
            contexto.append(
                {
                    "label": "Usuario",
                    "value": usuario.get("nombre_completo") or usuario.get("username") or f"#{filtros['id_usuario']}",
                }
            )

        estado_map = {
            "activos": "Productos activos",
            "inactivos": "Productos inactivos",
            "stock_bajo": "Solo stock bajo",
            "sin_stock": "Solo sin stock",
            "todos": "Todos los estados",
        }
        contexto.append(
            {
                "label": "Estado",
                "value": estado_map.get(filtros.get("estado_producto") or "activos", "Productos activos"),
            }
        )

        return contexto

    def _base_reporte(self, tipo, titulo, subtitulo, columnas, filas, formatos=None, resumen=None):
        return {
            "tipo": tipo,
            "titulo": titulo,
            "subtitulo": subtitulo,
            "columnas": columnas,
            "filas": filas,
            "formatos": formatos or {},
            "resumen": resumen or {},
            "nombre_archivo": _slug(titulo),
        }

    def _reporte_resumen_general(self, filtros, ctx, dashboard):
        productos_filtrados = ctx["productos_filtrados"]
        movimientos_filtrados = ctx["movimientos_filtrados"]
        productos_con_movimiento = {m.get("id_producto") for m in movimientos_filtrados}
        sin_movimiento = sum(1 for p in productos_filtrados if p.get("id") not in productos_con_movimiento)

        filas = [
            {
                "Indicador": "Total de productos visibles",
                "Valor": dashboard["kpis"]["total_productos"],
                "Detalle": "Productos que cumplen los filtros actuales.",
            },
            {
                "Indicador": "Total de categorias visibles",
                "Valor": dashboard["kpis"]["total_categorias"],
                "Detalle": "Categorias representadas en el inventario filtrado.",
            },
            {
                "Indicador": "Total de proveedores visibles",
                "Valor": dashboard["kpis"]["total_proveedores"],
                "Detalle": "Proveedores vinculados al resultado filtrado.",
            },
            {
                "Indicador": "Productos con stock bajo",
                "Valor": dashboard["kpis"]["productos_stock_bajo"],
                "Detalle": "Productos con cantidad igual o menor al stock minimo.",
            },
            {
                "Indicador": "Valor total del inventario",
                "Valor": dashboard["kpis"]["valor_total_inventario"],
                "Detalle": "Valorizado con el precio de venta actual.",
            },
            {
                "Indicador": "Costo total del inventario",
                "Valor": dashboard["kpis"]["costo_total_inventario"],
                "Detalle": "Valorizado con el precio de compra registrado.",
            },
            {
                "Indicador": "Entradas del periodo",
                "Valor": dashboard["kpis"]["entradas_periodo"],
                "Detalle": "Unidades de entrada en el rango filtrado.",
            },
            {
                "Indicador": "Salidas del periodo",
                "Valor": dashboard["kpis"]["salidas_periodo"],
                "Detalle": "Unidades de salida en el rango filtrado.",
            },
            {
                "Indicador": "Productos sin movimiento",
                "Valor": sin_movimiento,
                "Detalle": "Productos que no registran movimiento con los filtros aplicados.",
            },
        ]

        return self._base_reporte(
            "resumen_general",
            "Resumen general de reportes",
            "KPIs ejecutivos para seguimiento del inventario y la operacion.",
            ["Indicador", "Valor", "Detalle"],
            filas,
            formatos={"Valor": "metric"},
            resumen={
                "Productos visibles": dashboard["kpis"]["total_productos"],
                "Valor inventario": dashboard["kpis"]["valor_total_inventario"],
                "Entradas": dashboard["kpis"]["entradas_periodo"],
                "Salidas": dashboard["kpis"]["salidas_periodo"],
            },
        )

    def _reporte_stock_critico(self, filtros, ctx):
        filas = []
        for producto in ctx["productos_filtrados"]:
            cantidad = _safe_int(producto.get("cantidad"))
            stock_minimo = _safe_int(producto.get("stock_minimo"), 5)
            if cantidad > stock_minimo:
                continue
            precio_compra = _safe_float(producto.get("precio_compra"))
            precio_venta = _safe_float(producto.get("precio_unitario"))
            filas.append(
                {
                    "ID": producto.get("id"),
                    "Codigo": producto.get("codigo") or "",
                    "Producto": producto.get("nombre") or "",
                    "Categoria": producto.get("categoria_resuelta") or "General",
                    "Proveedor": producto.get("proveedor_resuelto") or "Sin proveedor",
                    "Stock": cantidad,
                    "Stock Minimo": stock_minimo,
                    "Stock Maximo": producto.get("stock_maximo"),
                    "Deficit": stock_minimo - cantidad,
                    "P. Compra": precio_compra or None,
                    "P. Venta": precio_venta,
                    "Valor Existencia": cantidad * precio_venta,
                }
            )

        filas.sort(key=lambda item: (item["Deficit"], -item["Stock"]), reverse=True)
        return self._base_reporte(
            "stock_critico",
            "Productos con stock critico",
            "Ayuda a priorizar reposiciones y prevenir quiebres de inventario.",
            [
                "ID",
                "Codigo",
                "Producto",
                "Categoria",
                "Proveedor",
                "Stock",
                "Stock Minimo",
                "Stock Maximo",
                "Deficit",
                "P. Compra",
                "P. Venta",
                "Valor Existencia",
            ],
            filas,
            formatos={
                "P. Compra": "currency",
                "P. Venta": "currency",
                "Valor Existencia": "currency",
            },
            resumen={
                "Productos criticos": len(filas),
                "Deficit acumulado": sum(_safe_int(item.get("Deficit")) for item in filas),
                "Valor comprometido": sum(_safe_float(item.get("Valor Existencia")) for item in filas),
            },
        )

    def _reporte_sin_movimiento(self, filtros, ctx):
        movimientos_por_producto = defaultdict(list)
        for movimiento in ctx["movimientos"]:
            movimientos_por_producto[movimiento.get("id_producto")].append(movimiento)

        productos_con_mov_filtrado = {m.get("id_producto") for m in ctx["movimientos_filtrados"]}
        hoy = datetime.now().date()
        filas = []

        for producto in ctx["productos_filtrados"]:
            if producto.get("id") in productos_con_mov_filtrado:
                continue

            historial = sorted(
                movimientos_por_producto.get(producto.get("id"), []),
                key=lambda item: item.get("fecha_dt") or datetime.min,
                reverse=True,
            )
            ultimo = historial[0] if historial else None
            ultima_fecha = ultimo.get("fecha_dt") if ultimo else None
            dias = (hoy - ultima_fecha.date()).days if ultima_fecha else None
            cantidad = _safe_int(producto.get("cantidad"))
            precio = _safe_float(producto.get("precio_unitario"))

            filas.append(
                {
                    "ID": producto.get("id"),
                    "Codigo": producto.get("codigo") or "",
                    "Producto": producto.get("nombre") or "",
                    "Categoria": producto.get("categoria_resuelta") or "General",
                    "Proveedor": producto.get("proveedor_resuelto") or "Sin proveedor",
                    "Stock": cantidad,
                    "Ultimo Movimiento": ultima_fecha,
                    "Dias Sin Movimiento": dias,
                    "Valor Inventario": cantidad * precio,
                }
            )

        filas.sort(
            key=lambda item: item.get("Dias Sin Movimiento")
            if item.get("Dias Sin Movimiento") is not None
            else 10**9,
            reverse=True,
        )
        return self._base_reporte(
            "sin_movimiento",
            "Productos sin movimiento",
            "Detecta inventario inmovilizado y oportunidades de depuracion comercial.",
            [
                "ID",
                "Codigo",
                "Producto",
                "Categoria",
                "Proveedor",
                "Stock",
                "Ultimo Movimiento",
                "Dias Sin Movimiento",
                "Valor Inventario",
            ],
            filas,
            formatos={"Ultimo Movimiento": "datetime", "Valor Inventario": "currency"},
            resumen={
                "Productos sin movimiento": len(filas),
                "Valor inmovilizado": sum(_safe_float(item.get("Valor Inventario")) for item in filas),
            },
        )

    def _reporte_productos_movidos(self, filtros, ctx, ascendente=False):
        agregados = defaultdict(
            lambda: {
                "entradas": 0,
                "salidas": 0,
                "movimientos": 0,
                "unidades": 0,
                "ultima_fecha": None,
            }
        )

        for movimiento in ctx["movimientos_filtrados"]:
            pid = movimiento.get("id_producto")
            tipo = str(movimiento.get("tipo_resuelto") or "").lower()
            cantidad = _safe_int(movimiento.get("cantidad"))
            agregados[pid]["movimientos"] += 1
            agregados[pid]["unidades"] += cantidad
            if "entrada" in tipo:
                agregados[pid]["entradas"] += cantidad
            elif "salida" in tipo:
                agregados[pid]["salidas"] += cantidad
            fecha = movimiento.get("fecha_dt")
            if fecha and (agregados[pid]["ultima_fecha"] is None or fecha > agregados[pid]["ultima_fecha"]):
                agregados[pid]["ultima_fecha"] = fecha

        filas = []
        for pid, data in agregados.items():
            if data["movimientos"] <= 0:
                continue
            producto = ctx["productos_by_id"].get(pid) or {}
            filas.append(
                {
                    "ID": pid,
                    "Codigo": producto.get("codigo") or "",
                    "Producto": producto.get("nombre") or "",
                    "Categoria": producto.get("categoria_resuelta") or "General",
                    "Entradas": data["entradas"],
                    "Salidas": data["salidas"],
                    "Total Movimientos": data["movimientos"],
                    "Unidades Movidas": data["unidades"],
                    "Ultimo Movimiento": data["ultima_fecha"],
                }
            )

        filas.sort(
            key=lambda item: (item["Unidades Movidas"], item["Total Movimientos"]),
            reverse=not ascendente,
        )
        tipo = "menos_movidos" if ascendente else "mas_movidos"
        titulo = "Productos menos movidos" if ascendente else "Productos mas movidos"
        subtitulo = (
            "Identifica productos con baja rotacion dentro del periodo filtrado."
            if ascendente
            else "Mide la rotacion para identificar los productos de mayor actividad."
        )
        return self._base_reporte(
            tipo,
            titulo,
            subtitulo,
            [
                "ID",
                "Codigo",
                "Producto",
                "Categoria",
                "Entradas",
                "Salidas",
                "Total Movimientos",
                "Unidades Movidas",
                "Ultimo Movimiento",
            ],
            filas,
            formatos={"Ultimo Movimiento": "datetime"},
            resumen={
                "Productos analizados": len(filas),
                "Unidades movidas": sum(_safe_int(item.get("Unidades Movidas")) for item in filas),
            },
        )

    def _reporte_inventario_valorizado(self, filtros, ctx):
        filas = []
        costo_total = 0.0
        venta_total = 0.0

        for producto in ctx["productos_filtrados"]:
            cantidad = _safe_int(producto.get("cantidad"))
            precio_compra = _safe_float(producto.get("precio_compra"))
            precio_venta = _safe_float(producto.get("precio_unitario"))
            costo = cantidad * precio_compra
            valor_venta = cantidad * precio_venta
            margen_pct = ((precio_venta - precio_compra) / precio_compra * 100) if precio_compra > 0 else None
            costo_total += costo
            venta_total += valor_venta

            filas.append(
                {
                    "ID": producto.get("id"),
                    "Codigo": producto.get("codigo") or "",
                    "Producto": producto.get("nombre") or "",
                    "Categoria": producto.get("categoria_resuelta") or "General",
                    "Proveedor": producto.get("proveedor_resuelto") or "Sin proveedor",
                    "Stock": cantidad,
                    "P. Compra": precio_compra or None,
                    "P. Venta": precio_venta,
                    "Costo Total": costo,
                    "Valor Venta": valor_venta,
                    "Margen %": margen_pct,
                }
            )

        filas.sort(key=lambda item: _safe_float(item.get("Valor Venta")), reverse=True)
        return self._base_reporte(
            "inventario_valorizado",
            "Inventario valorizado",
            "Consolida costo, valor de venta y margen estimado del inventario actual.",
            [
                "ID",
                "Codigo",
                "Producto",
                "Categoria",
                "Proveedor",
                "Stock",
                "P. Compra",
                "P. Venta",
                "Costo Total",
                "Valor Venta",
                "Margen %",
            ],
            filas,
            formatos={
                "P. Compra": "currency",
                "P. Venta": "currency",
                "Costo Total": "currency",
                "Valor Venta": "currency",
                "Margen %": "percent",
            },
            resumen={
                "Productos valorizados": len(filas),
                "Costo total": costo_total,
                "Valor total de venta": venta_total,
                "Margen estimado": venta_total - costo_total,
            },
        )

    def _reporte_movimientos_usuario(self, filtros, ctx):
        agregados = defaultdict(
            lambda: {
                "Usuario": "Sistema",
                "Nombre": "Sistema",
                "Rol": "Sistema",
                "Movimientos": 0,
                "Entradas": 0,
                "Salidas": 0,
                "Ajustes": 0,
                "Ultima Actividad": None,
            }
        )

        for movimiento in ctx["movimientos_filtrados"]:
            usuario_id = movimiento.get("id_usuario") or 0
            fila = agregados[usuario_id]
            fila["Usuario"] = movimiento.get("usuario_nombre") or "Sistema"
            fila["Nombre"] = movimiento.get("usuario_completo") or fila["Usuario"]
            fila["Rol"] = movimiento.get("rol_usuario") or "Sistema"
            fila["Movimientos"] += 1

            tipo = str(movimiento.get("tipo_resuelto") or "").lower()
            cantidad = _safe_int(movimiento.get("cantidad"))
            if "entrada" in tipo:
                fila["Entradas"] += cantidad
            elif "salida" in tipo:
                fila["Salidas"] += cantidad
            else:
                fila["Ajustes"] += cantidad

            fecha = movimiento.get("fecha_dt")
            if fecha and (fila["Ultima Actividad"] is None or fecha > fila["Ultima Actividad"]):
                fila["Ultima Actividad"] = fecha

        filas = sorted(
            agregados.values(),
            key=lambda item: (item["Movimientos"], item["Entradas"] + item["Salidas"] + item["Ajustes"]),
            reverse=True,
        )
        return self._base_reporte(
            "movimientos_usuario",
            "Movimientos por usuario",
            "Resume la actividad operativa por usuario dentro del periodo filtrado.",
            [
                "Usuario",
                "Nombre",
                "Rol",
                "Movimientos",
                "Entradas",
                "Salidas",
                "Ajustes",
                "Ultima Actividad",
            ],
            filas,
            formatos={"Ultima Actividad": "datetime"},
            resumen={
                "Usuarios con actividad": len(filas),
                "Movimientos analizados": sum(_safe_int(item.get("Movimientos")) for item in filas),
            },
        )

    def _reporte_por_proveedor(self, filtros, ctx):
        movimientos_por_proveedor = {}
        for movimiento in ctx["movimientos_filtrados"] or ctx["movimientos"]:
            pid = movimiento.get("id_proveedor") or movimiento.get("proveedor_producto") or "Sin proveedor"
            fecha = movimiento.get("fecha_dt")
            if fecha and (pid not in movimientos_por_proveedor or fecha > movimientos_por_proveedor[pid]):
                movimientos_por_proveedor[pid] = fecha

        agregados = defaultdict(
            lambda: {
                "Proveedor": "Sin proveedor",
                "RUC/NIT": "",
                "Telefono": "",
                "Productos": 0,
                "Stock Total": 0,
                "Valor Inventario": 0.0,
                "Productos Criticos": 0,
                "Ultimo Movimiento": None,
            }
        )

        for producto in ctx["productos_filtrados"]:
            proveedor_id = producto.get("id_proveedor") or producto.get("proveedor_resuelto") or "Sin proveedor"
            proveedor_info = ctx["proveedores_by_id"].get(producto.get("id_proveedor")) or {}
            fila = agregados[proveedor_id]
            fila["Proveedor"] = producto.get("proveedor_resuelto") or "Sin proveedor"
            fila["RUC/NIT"] = proveedor_info.get("ruc_nit") or ""
            fila["Telefono"] = proveedor_info.get("telefono") or ""
            fila["Productos"] += 1
            fila["Stock Total"] += _safe_int(producto.get("cantidad"))
            fila["Valor Inventario"] += _safe_int(producto.get("cantidad")) * _safe_float(producto.get("precio_unitario"))
            if _safe_int(producto.get("cantidad")) <= _safe_int(producto.get("stock_minimo"), 5):
                fila["Productos Criticos"] += 1
            fila["Ultimo Movimiento"] = movimientos_por_proveedor.get(proveedor_id)

        filas = sorted(
            agregados.values(),
            key=lambda item: (item["Valor Inventario"], item["Productos"]),
            reverse=True,
        )
        return self._base_reporte(
            "por_proveedor",
            "Reporte por proveedor",
            "Consolida inventario, criticidad y valor asociado por proveedor.",
            [
                "Proveedor",
                "RUC/NIT",
                "Telefono",
                "Productos",
                "Stock Total",
                "Valor Inventario",
                "Productos Criticos",
                "Ultimo Movimiento",
            ],
            filas,
            formatos={"Valor Inventario": "currency", "Ultimo Movimiento": "datetime"},
            resumen={
                "Proveedores visibles": len(filas),
                "Valor inventario": sum(_safe_float(item.get("Valor Inventario")) for item in filas),
            },
        )

    def _reporte_comparativo_fechas(self, filtros, ctx):
        fecha_fin = _as_date(filtros.get("fecha_fin")) or datetime.now().date()
        fecha_inicio = _as_date(filtros.get("fecha_inicio")) or (fecha_fin - timedelta(days=29))
        dias = max((fecha_fin - fecha_inicio).days + 1, 1)
        fecha_fin_prev = fecha_inicio - timedelta(days=1)
        fecha_inicio_prev = fecha_fin_prev - timedelta(days=dias - 1)

        filtros_actual = dict(filtros, fecha_inicio=fecha_inicio.isoformat(), fecha_fin=fecha_fin.isoformat())
        filtros_prev = dict(filtros, fecha_inicio=fecha_inicio_prev.isoformat(), fecha_fin=fecha_fin_prev.isoformat())

        movs_actual = self._filtrar_movimientos_reportes(ctx["movimientos"], filtros_actual)
        movs_prev = self._filtrar_movimientos_reportes(ctx["movimientos"], filtros_prev)

        resumen_actual = self._resumen_periodo(movs_actual)
        resumen_prev = self._resumen_periodo(movs_prev)

        def _variacion(actual, anterior):
            diferencia = actual - anterior
            porcentaje = ((diferencia / anterior) * 100) if anterior else None
            return diferencia, porcentaje

        filas = []
        metricas = [
            ("Entradas (und)", "entradas_unidades"),
            ("Salidas (und)", "salidas_unidades"),
            ("Balance neto", "balance_unidades"),
            ("Movimientos", "total_movimientos"),
            ("Productos con movimiento", "productos_con_movimiento"),
            ("Valor de entradas", "valor_entradas"),
            ("Valor de salidas", "valor_salidas"),
        ]

        for etiqueta, clave in metricas:
            actual = resumen_actual[clave]
            anterior = resumen_prev[clave]
            variacion, variacion_pct = _variacion(actual, anterior)
            filas.append(
                {
                    "Metrica": etiqueta,
                    "Periodo Actual": actual,
                    "Periodo Anterior": anterior,
                    "Variacion": variacion,
                    "Variacion %": variacion_pct,
                }
            )

        return self._base_reporte(
            "comparativo_fechas",
            "Comparativo por rango de fechas",
            "Compara el comportamiento del periodo actual frente al periodo inmediatamente anterior.",
            ["Metrica", "Periodo Actual", "Periodo Anterior", "Variacion", "Variacion %"],
            filas,
            formatos={
                "Variacion %": "percent",
                "Periodo Actual": "auto",
                "Periodo Anterior": "auto",
                "Variacion": "auto",
            },
            resumen={
                "Periodo actual": f"{fecha_inicio.isoformat()} a {fecha_fin.isoformat()}",
                "Periodo anterior": f"{fecha_inicio_prev.isoformat()} a {fecha_fin_prev.isoformat()}",
            },
        )

    def _reporte_entradas_vs_salidas(self, filtros, ctx):
        por_fecha = defaultdict(lambda: {"Entradas": 0, "Salidas": 0, "Movimientos": 0})
        for movimiento in ctx["movimientos_filtrados"]:
            fecha = movimiento.get("fecha_date")
            if not fecha:
                continue
            tipo = str(movimiento.get("tipo_resuelto") or "").lower()
            cantidad = _safe_int(movimiento.get("cantidad"))
            por_fecha[fecha]["Movimientos"] += 1
            if "entrada" in tipo:
                por_fecha[fecha]["Entradas"] += cantidad
            elif "salida" in tipo:
                por_fecha[fecha]["Salidas"] += cantidad

        filas = []
        for fecha, data in sorted(por_fecha.items()):
            filas.append(
                {
                    "Fecha": fecha,
                    "Entradas": data["Entradas"],
                    "Salidas": data["Salidas"],
                    "Balance": data["Entradas"] - data["Salidas"],
                    "Movimientos": data["Movimientos"],
                }
            )

        return self._base_reporte(
            "entradas_vs_salidas",
            "Entradas vs salidas",
            "Muestra el comportamiento diario del flujo de inventario en el periodo filtrado.",
            ["Fecha", "Entradas", "Salidas", "Balance", "Movimientos"],
            filas,
            formatos={"Fecha": "date"},
            resumen={
                "Dias con actividad": len(filas),
                "Entradas": sum(_safe_int(item.get("Entradas")) for item in filas),
                "Salidas": sum(_safe_int(item.get("Salidas")) for item in filas),
            },
        )

    def obtener_catalogo_reportes_dinamicos(self):
        self.ping_and_commit()
        filtros = self._normalizar_filtros_reportes({"estado_producto": "todos"})
        ctx = self._snapshot_reportes(filtros)
        return DynamicReportsService(self, ctx, filtros).catalog()

    def generar_grafico_dinamico(self, configuracion, filtros=None):
        self.ping_and_commit()
        filtros = self._normalizar_filtros_reportes(filtros)
        ctx = self._snapshot_reportes(filtros)
        return DynamicReportsService(self, ctx, filtros).build_chart(configuracion)

    def generar_reporte_personalizado(self, configuracion, filtros=None):
        self.ping_and_commit()
        filtros = self._normalizar_filtros_reportes(filtros)
        ctx = self._snapshot_reportes(filtros)
        return DynamicReportsService(self, ctx, filtros).build_report(configuracion)

    def obtener_panel_reportes(self, tipo_reporte, filtros=None):
        self.ping_and_commit()
        filtros = self._normalizar_filtros_reportes(filtros)
        ctx = self._snapshot_reportes(filtros)
        dashboard = self._construir_dashboard_reportes(filtros, ctx)

        constructores = {
            "resumen_general": lambda: self._reporte_resumen_general(filtros, ctx, dashboard),
            "stock_critico": lambda: self._reporte_stock_critico(filtros, ctx),
            "sin_movimiento": lambda: self._reporte_sin_movimiento(filtros, ctx),
            "mas_movidos": lambda: self._reporte_productos_movidos(filtros, ctx, ascendente=False),
            "menos_movidos": lambda: self._reporte_productos_movidos(filtros, ctx, ascendente=True),
            "inventario_valorizado": lambda: self._reporte_inventario_valorizado(filtros, ctx),
            "movimientos_usuario": lambda: self._reporte_movimientos_usuario(filtros, ctx),
            "por_proveedor": lambda: self._reporte_por_proveedor(filtros, ctx),
            "comparativo_fechas": lambda: self._reporte_comparativo_fechas(filtros, ctx),
            "entradas_vs_salidas": lambda: self._reporte_entradas_vs_salidas(filtros, ctx),
        }

        reporte = constructores.get(tipo_reporte, constructores["resumen_general"])()
        return {
            "filtros": filtros,
            "reporte": reporte,
            "dashboard": dashboard,
            "historial": self.obtener_historial_reportes(),
        }

    def registrar_reporte_generado(
        self,
        tipo_reporte,
        titulo_reporte,
        id_usuario=None,
        username="",
        filtros=None,
        formato="Vista previa",
        total_registros=0,
    ):
        try:
            self.ping_and_commit()
            filtros_json = json.dumps(filtros or {}, ensure_ascii=False)
            self.cursor.execute(
                """
                INSERT INTO reportes_generados
                (tipo_reporte, titulo_reporte, id_usuario, username, filtros_json, formato, total_registros)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tipo_reporte,
                    titulo_reporte,
                    id_usuario,
                    username,
                    filtros_json,
                    formato,
                    total_registros,
                ),
            )
            self.connection.commit()
            return True
        except Error as exc:
            print(f"[WARN] registrar_reporte_generado: {exc}")
            return False

    def obtener_historial_reportes(self, limite=200):
        try:
            self.ping_and_commit()
            self.cursor.execute(
                """
                SELECT id, tipo_reporte, titulo_reporte, username, formato,
                       filtros_json, total_registros, fecha_generacion
                FROM reportes_generados
                ORDER BY fecha_generacion DESC
                LIMIT %s
                """,
                (limite,),
            )
            return self.cursor.fetchall()
        except Error as exc:
            print(f"[WARN] historial reportes: {exc}")
            return []
