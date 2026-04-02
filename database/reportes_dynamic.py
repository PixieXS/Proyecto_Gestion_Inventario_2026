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

    