REPORTES_DISPONIBLES = [
    ("resumen_general", "Resumen general con KPIs"),
    ("stock_critico", "Productos con stock critico"),
    ("sin_movimiento", "Productos sin movimiento"),
    ("mas_movidos", "Productos mas movidos"),
    ("menos_movidos", "Productos menos movidos"),
    ("inventario_valorizado", "Inventario valorizado"),
    ("movimientos_usuario", "Movimientos por usuario"),
    ("por_proveedor", "Reporte por proveedor"),
    ("comparativo_fechas", "Comparativo por rango de fechas"),
    ("entradas_vs_salidas", "Entradas vs salidas"),
]

RANK_CHART_TYPES = ("Barras horizontales", "Barras verticales", "Linea", "Pastel", "Dona")
TREND_CHART_TYPES = ("Linea", "Barras verticales")
TOP_OPTIONS = ("Top 5", "Top 10", "Top 15")
TREND_OPTIONS = ("Ultimos 7", "Ultimos 15", "Ultimos 30")

CATEGORY_METRICS = {
    "Valor inventario": {"field": "valor_total", "format": "currency"},
    "Stock": {"field": "stock_total", "format": "number"},
    "Productos por categoria": {"field": "productos", "format": "number"},
}
PRODUCT_METRICS = {
    "Movimientos": {"field": "movimientos", "format": "number"},
    "Stock": {"field": "stock_actual", "format": "number"},
    "Valor inventario": {"field": "valor_inventario", "format": "currency"},
}
SUPPLIER_METRICS = {
    "Valor inventario": {"field": "valor_total", "format": "currency"},
    "Stock": {"field": "stock_total", "format": "number"},
    "Productos": {"field": "productos", "format": "number"},
    "Productos criticos": {"field": "productos_criticos", "format": "number"},
}
TREND_METRICS = {
    "Entradas": {"field": "entradas", "format": "number", "color_role": "secondary"},
    "Salidas": {"field": "salidas", "format": "number", "color_role": "danger"},
    "Balance": {"field": "balance", "format": "number", "color_role": "primary"},
    "Movimientos": {"field": "movimientos", "format": "number", "color_role": "warning"},
}


def as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def label_limit(texto):
    numeros = "".join(ch for ch in str(texto or "") if ch.isdigit())
    return max(int(numeros or 10), 1)


def safe_label(texto, limit=28):
    texto = str(texto or "")
    return texto if len(texto) <= limit else f"{texto[: limit - 3]}..."
