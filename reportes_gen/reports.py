import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import HRFlowable, LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import REPORTS_PATH


COLUMNAS_INVENTARIO = {
    "ID": lambda p: p["id"],
    "Codigo": lambda p: p.get("codigo") or "",
    "Producto": lambda p: p["nombre"],
    "Descripcion": lambda p: (p.get("descripcion") or "")[:120],
    "Categoria": lambda p: p.get("categoria", "General"),
    "Stock": lambda p: p["cantidad"],
    "Stock Minimo": lambda p: p.get("stock_minimo", 5),
    "Precio": lambda p: float(p.get("precio_unitario") or 0),
    "Proveedor": lambda p: p.get("proveedor") or "N/A",
    "Ultima Act.": lambda p: p.get("ultima_actualizacion", ""),
}

COLUMNAS_MOVIMIENTOS = {
    "ID": lambda m: m["id"],
    "Producto": lambda m: m.get("nombre_producto", ""),
    "Tipo": lambda m: m.get("tipo_movimiento", ""),
    "Cantidad": lambda m: m["cantidad"],
    "Fecha": lambda m: m.get("fecha"),
    "Usuario": lambda m: m.get("usuario_nombre") or "Sistema",
    "Categoria": lambda m: m.get("categoria_producto", ""),
    "Nota": lambda m: (m.get("descripcion") or "")[:120],
}


def _hex_to_color(hex_str):
    return colors.HexColor(f"#{str(hex_str or '#1F4788').lstrip('#')}")


def _lighten(hex_str, factor=0.92):
    raw = str(hex_str or "#1F4788").lstrip("#")
    r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return colors.HexColor(f"#{r:02x}{g:02x}{b:02x}")


def _slug(texto):
    limpio = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(texto or "reporte"))
    while "__" in limpio:
        limpio = limpio.replace("__", "_")
    return limpio.strip("_") or "reporte"


class ReportGenerator:
    def __init__(self):
        os.makedirs(REPORTS_PATH, exist_ok=True)
        self.styles = getSampleStyleSheet()

    def _style(self, name, **kwargs):
        return ParagraphStyle(name, parent=self.styles["Normal"], **kwargs)

    def _titulo_style(self, color_hex):
        return self._style("TituloBI", fontSize=18, leading=22, textColor=_hex_to_color(color_hex), fontName="Helvetica-Bold", spaceAfter=4, alignment=1)

    def _subtitulo_style(self):
        return self._style("SubBI", fontSize=9, leading=12, textColor=colors.HexColor("#64748B"), alignment=1, spaceAfter=2)

    def _section_style(self):
        return self._style("SectionBI", fontSize=10, leading=12, fontName="Helvetica-Bold", textColor=colors.HexColor("#1E293B"), spaceAfter=6)

    def _cell_style(self, font_size=8):
        return self._style("CellBI", fontSize=font_size, leading=font_size + 2, textColor=colors.HexColor("#1E293B"), wordWrap="CJK")

    def _header_style(self, font_size=9):
        return self._style("HdrBI", fontSize=font_size, leading=font_size + 2, textColor=colors.white, fontName="Helvetica-Bold")

    def _empresa_style(self):
        return self._style("EmpBI", fontSize=11, leading=13, fontName="Helvetica-Bold", textColor=colors.HexColor("#1E293B"), alignment=1, spaceAfter=2)

    def _texto_filtros(self, filtros):
        etiquetas = {
            "fecha_inicio": "Fecha inicio",
            "fecha_fin": "Fecha fin",
            "categoria": "Categoria",
            "id_proveedor": "Proveedor",
            "id_producto": "Producto",
            "tipo_movimiento": "Tipo movimiento",
            "id_usuario": "Usuario",
            "estado_producto": "Estado producto",
        }
        filas = []
        for clave, valor in (filtros or {}).items():
            if valor in (None, "", "todos"):
                continue
            filas.append((etiquetas.get(clave, clave), valor))
        return filas or [("Filtros", "Sin filtros adicionales")]

    @staticmethod
    def _formato_por_fila(reporte, columna, fila):
        formatos = dict(reporte.get("formatos") or {})
        fmt = formatos.get(columna)
        if fmt == "auto" and reporte.get("tipo") == "comparativo_fechas":
            metrica = str(fila.get("Metrica") or "").lower()
            return "currency" if "valor" in metrica else "number"
        if fmt == "metric":
            valor = fila.get(columna)
            return "currency" if isinstance(valor, float) else "number"
        return fmt

    def _formatear_valor(self, valor, fmt=None):
        if valor in (None, ""):
            return ""
        if fmt == "currency":
            return f"${float(valor):,.2f}"
        if fmt == "percent":
            return f"{float(valor):,.1f}%"
        if fmt == "number":
            return f"{int(float(valor)):,}"
        if fmt == "date" and hasattr(valor, "strftime"):
            return valor.strftime("%d/%m/%Y")
        if fmt == "datetime" and hasattr(valor, "strftime"):
            return valor.strftime("%d/%m/%Y %H:%M")
        return str(valor)

    def _membrete(self, empresa_info, color_hex):
        elementos = []
        nombre = (empresa_info or {}).get("nombre") or "Mi Empresa"
        elementos.append(Paragraph(nombre, self._empresa_style()))
        partes = []
        if (empresa_info or {}).get("direccion"):
            partes.append(empresa_info["direccion"])
        if (empresa_info or {}).get("telefono"):
            partes.append(f"Tel: {empresa_info['telefono']}")
        if partes:
            elementos.append(Paragraph(" | ".join(partes), self._subtitulo_style()))
        elementos.append(Spacer(1, 0.18 * cm))
        elementos.append(HRFlowable(width="100%", thickness=2, color=_hex_to_color(color_hex), spaceAfter=8))
        return elementos

    def _estimar_colwidths(self, headers, rows, available_width, font_size):
        font_name = "Helvetica"
        min_width = 2.1 * cm
        max_width = max(4.2 * cm, available_width * 0.36)
        widths = []
        samples = rows[:60]
        for idx, header in enumerate(headers):
            valores = [str(header)]
            valores.extend(str(row[idx])[:90] for row in samples if idx < len(row))
            raw_width = max(pdfmetrics.stringWidth(texto, font_name, font_size) for texto in valores) + 12
            widths.append(max(min_width, min(raw_width, max_width)))
        total = sum(widths)
        if total <= available_width:
            return widths
        escala = available_width / total
        ajustadas = [max(min_width, width * escala) for width in widths]
        exceso = sum(ajustadas) - available_width
        if exceso <= 0:
            return ajustadas
        flexibles = [idx for idx, width in enumerate(ajustadas) if width > min_width]
        while exceso > 0.5 and flexibles:
            descuento = exceso / len(flexibles)
            nuevos = []
            for idx in flexibles:
                ajustadas[idx] = max(min_width, ajustadas[idx] - descuento)
                if ajustadas[idx] > min_width:
                    nuevos.append(idx)
            exceso = sum(ajustadas) - available_width
            flexibles = nuevos
        return ajustadas

    def _tabla_clave_valor(self, filas, color_hex, widths):
        data = [[Paragraph("Campo", self._header_style()), Paragraph("Valor", self._header_style())]]
        cell_style = self._cell_style()
        for clave, valor in filas:
            data.append([Paragraph(str(clave), cell_style), Paragraph(str(valor), cell_style)])
        tabla = Table(data, colWidths=widths)
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _hex_to_color(color_hex)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return tabla

    def _tabla_resumen(self, resumen, available_width, color_hex):
        items = list((resumen or {}).items())
        if not items:
            return None
        columnas = 2 if len(items) <= 4 else 3
        card_width = available_width / columnas
        filas = []
        fila_actual = []
        for clave, valor in items:
            contenido = [
                Paragraph(str(clave), self._style("KpiLabelBI", fontSize=8, leading=10, textColor=colors.HexColor("#64748B"), fontName="Helvetica-Bold")),
                Spacer(1, 0.05 * cm),
                Paragraph(self._formatear_valor(valor, "currency" if isinstance(valor, float) else None), self._style("KpiValueBI", fontSize=12, leading=14, textColor=colors.HexColor("#1E293B"), fontName="Helvetica-Bold")),
            ]
            card = Table([[contenido]], colWidths=[card_width - 8])
            card.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), _lighten(color_hex)),
                        ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            fila_actual.append(card)
            if len(fila_actual) == columnas:
                filas.append(fila_actual)
                fila_actual = []
        if fila_actual:
            while len(fila_actual) < columnas:
                fila_actual.append("")
            filas.append(fila_actual)
        tabla = Table(filas, colWidths=[card_width] * columnas)
        tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return tabla

    def _tabla_detalle(self, reporte, available_width, color_hex):
        columnas = list(reporte.get("columnas") or [])
        filas = list(reporte.get("filas") or [])
        if not columnas or not filas:
            return None
        font_size = 8 if len(columnas) <= 8 else 7
        headers = [Paragraph(str(col), self._header_style(font_size + 0.3)) for col in columnas]
        rows_plain = []
        data = [headers]
        alignments = []
        for col_idx, columna in enumerate(columnas):
            fmt = self._formato_por_fila(reporte, columna, filas[0] if filas else {})
            alignments.append("RIGHT" if fmt in {"currency", "number", "percent"} else "LEFT")
        for fila in filas:
            row_plain = []
            row_render = []
            for columna in columnas:
                texto = self._formatear_valor(fila.get(columna), self._formato_por_fila(reporte, columna, fila))
                row_plain.append(texto)
                row_render.append(Paragraph(texto, self._cell_style(font_size)))
            rows_plain.append(row_plain)
            data.append(row_render)
        widths = self._estimar_colwidths(columnas, rows_plain, available_width, font_size)
        tabla = LongTable(data, colWidths=widths, repeatRows=1)
        estilos = [
            ("BACKGROUND", (0, 0), (-1, 0), _hex_to_color(color_hex)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        for idx, alignment in enumerate(alignments):
            estilos.append(("ALIGN", (idx, 1), (idx, -1), alignment))
        tabla.setStyle(TableStyle(estilos))
        return tabla

    def _doc(self, filename, pagesize):
        return SimpleDocTemplate(filename, pagesize=pagesize, leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.8 * cm, bottomMargin=1.6 * cm)

    def generar_reporte_ejecutivo(self, reporte, filtros=None, usuario=None, empresa_info=None, color_hex="#1F4788"):
        try:
            nombre = reporte.get("nombre_archivo") or _slug(reporte.get("titulo") or "reporte")
            filename = f"{REPORTS_PATH}{nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            columnas = list(reporte.get("columnas") or [])
            filas = list(reporte.get("filas") or [])
            ancho_estimado = sum(
                max(len(str(columna)), max((len(self._formatear_valor(fila.get(columna), self._formato_por_fila(reporte, columna, fila))) for fila in filas[:20]), default=0))
                for columna in columnas
            )
            usa_horizontal = len(columnas) > 7 or ancho_estimado > 95
            pagesize = landscape(A4) if usa_horizontal else A4
            doc = self._doc(filename, pagesize)
            available_width = pagesize[0] - doc.leftMargin - doc.rightMargin

            def footer(canvas, pdf_doc):
                canvas.saveState()
                canvas.setFont("Helvetica", 8)
                canvas.setFillColor(colors.HexColor("#64748B"))
                canvas.drawRightString(pdf_doc.pagesize[0] - pdf_doc.rightMargin, 0.9 * cm, f"Pagina {canvas.getPageNumber()}")
                canvas.restoreState()

            elementos = []
            if empresa_info:
                elementos.extend(self._membrete(empresa_info, color_hex))
            elementos.append(Paragraph((reporte.get("titulo") or "Reporte").upper(), self._titulo_style(color_hex)))
            if reporte.get("subtitulo"):
                elementos.append(Paragraph(reporte["subtitulo"], self._subtitulo_style()))
            usuario_label = (usuario or {}).get("username") or "Sistema"
            elementos.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Usuario: {usuario_label}", self._subtitulo_style()))
            elementos.append(Spacer(1, 0.18 * cm))

            elementos.append(Paragraph("Filtros aplicados", self._section_style()))
            elementos.append(self._tabla_clave_valor(self._texto_filtros(filtros), color_hex, [4.2 * cm, available_width - 4.2 * cm]))
            elementos.append(Spacer(1, 0.28 * cm))

            tabla_resumen = self._tabla_resumen(reporte.get("resumen") or {}, available_width, color_hex)
            if tabla_resumen is not None:
                elementos.append(Paragraph("Resumen ejecutivo", self._section_style()))
                elementos.append(tabla_resumen)
                elementos.append(Spacer(1, 0.28 * cm))

            tabla_detalle = self._tabla_detalle(reporte, available_width, color_hex)
            elementos.append(Paragraph("Detalle del reporte", self._section_style()))
            if tabla_detalle is not None:
                elementos.append(tabla_detalle)
            else:
                elementos.append(Paragraph("No hay datos para mostrar con los filtros seleccionados.", self._subtitulo_style()))

            doc.build(elementos, onFirstPage=footer, onLaterPages=footer)
            return True, f"Guardado en:\n{filename}"
        except Exception as exc:
            return False, str(exc)

    def _reporte_desde_tabla(self, tipo, titulo, columnas, data_rows, formatos=None, resumen=None, subtitulo=""):
        filas = []
        for row in data_rows:
            fila = {}
            for idx, columna in enumerate(columnas):
                fila[columna] = row[idx]
            filas.append(fila)
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

    def generar_reporte_inventario(self, productos, columnas=None, color_hex="#1F4788", empresa_info=None):
        cols = columnas or list(COLUMNAS_INVENTARIO.keys())
        rows = [[COLUMNAS_INVENTARIO[col](producto) for col in cols] for producto in productos]
        reporte = self._reporte_desde_tabla("inventario", "Reporte de Inventario", cols, rows, formatos={"Precio": "currency"})
        return self.generar_reporte_ejecutivo(reporte, empresa_info=empresa_info, color_hex=color_hex)

    def generar_reporte_movimientos(self, movimientos, productos_dict=None, titulo=None, columnas=None, color_hex="#1F4788", empresa_info=None):
        cols = columnas or list(COLUMNAS_MOVIMIENTOS.keys())
        rows = [[COLUMNAS_MOVIMIENTOS[col](movimiento) for col in cols] for movimiento in movimientos]
        reporte = self._reporte_desde_tabla("movimientos", titulo or "Reporte de Movimientos", cols, rows, formatos={"Cantidad": "number", "Fecha": "datetime"})
        return self.generar_reporte_ejecutivo(reporte, empresa_info=empresa_info, color_hex=color_hex)

    def generar_reporte_estadisticas(self, estadisticas, color_hex="#1F4788", empresa_info=None):
        rows = [
            ["Total de Productos Activos", estadisticas.get("total_productos", 0)],
            ["Stock Total (Unidades)", estadisticas.get("stock_total", 0)],
            ["Valor Total Inventario", estadisticas.get("valor_total", 0.0)],
            ["Productos con Stock Bajo/Critico", estadisticas.get("bajo_stock", 0)],
            ["Total de Proveedores", estadisticas.get("total_proveedores", 0)],
            ["Productos Inhabilitados", estadisticas.get("productos_inactivos", 0)],
        ]
        reporte = self._reporte_desde_tabla(
            "estadisticas",
            "Reporte de Estadisticas",
            ["Metrica", "Valor"],
            rows,
            formatos={"Valor": "metric"},
            resumen={"Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")},
        )
        return self.generar_reporte_ejecutivo(reporte, empresa_info=empresa_info, color_hex=color_hex)
