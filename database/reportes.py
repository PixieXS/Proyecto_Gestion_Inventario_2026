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
