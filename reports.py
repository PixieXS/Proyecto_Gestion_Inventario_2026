from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from datetime import datetime
import os
from config import REPORTS_PATH


class ReportGenerator:
    def __init__(self):
        if not os.path.exists(REPORTS_PATH):
            os.makedirs(REPORTS_PATH)
        self.styles = getSampleStyleSheet()
        self.cell_style = ParagraphStyle(
            'Cell', parent=self.styles['Normal'], fontSize=8, leading=10, wordWrap='CJK')
        self.hdr_style = ParagraphStyle(
            'Hdr', parent=self.styles['Normal'], fontSize=9, leading=11,
            textColor=colors.whitesmoke, fontName='Helvetica-Bold')

    def _p(self, txt):
        return Paragraph(str(txt) if txt is not None else '', self.cell_style)

    def _ph(self, txt):
        return Paragraph(str(txt), self.hdr_style)

    def _doc_landscape(self, filename):
        return SimpleDocTemplate(filename, pagesize=landscape(A4),
                                 leftMargin=1.5*cm, rightMargin=1.5*cm,
                                 topMargin=2*cm, bottomMargin=2*cm)

    def _titulo_style(self):
        return ParagraphStyle('T', parent=self.styles['Heading1'],
                              fontSize=20, textColor=colors.HexColor('#1f4788'),
                              spaceAfter=16, alignment=1)

    def _table_style(self):
        return TableStyle([
            ('BACKGROUND',  (0, 0), (-1, 0),  colors.HexColor('#1f4788')),
            ('TEXTCOLOR',   (0, 0), (-1, 0),  colors.whitesmoke),
            ('ALIGN',       (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f4ff')]),
            ('GRID',        (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',(0, 0), (-1, -1), 4),
            ('TOPPADDING',  (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING',(0,0), (-1, -1), 4),
        ])

    # ── Inventario ────────────────────────────────────────────────────────────

    def generar_reporte_inventario(self, productos):
        try:
            fn = f"{REPORTS_PATH}Inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            doc = self._doc_landscape(fn)
            els = [
                Paragraph("REPORTE DE INVENTARIO", self._titulo_style()),
                Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                          self.styles['Normal']),
                Spacer(1, 0.25*inch),
            ]
            data = [[self._ph(h) for h in
                     ['ID','Producto','Descripción','Categoría','Cantidad',
                      'Stock Mín','Precio Unit.','Proveedor']]]
            for p in productos:
                desc = (p.get('descripcion') or '')[:80]
                data.append([
                    self._p(p['id']), self._p(p['nombre']), self._p(desc),
                    self._p(p.get('categoria','General')), self._p(p['cantidad']),
                    self._p(p.get('stock_minimo', 5)),
                    self._p(f"${float(p['precio_unitario']):.2f}"),
                    self._p(p.get('proveedor') or 'N/A'),
                ])
            cols = [1.0*cm, 4.8*cm, 5.5*cm, 3*cm, 1.8*cm, 1.8*cm, 2.5*cm, 4*cm]
            t = Table(data, colWidths=cols, repeatRows=1)
            t.setStyle(self._table_style())
            els.append(t)
            doc.build(els)
            return True, f"Guardado en: {fn}"
        except Exception as e:
            return False, str(e)

    # ── Movimientos ───────────────────────────────────────────────────────────

    def generar_reporte_movimientos(self, movimientos, productos_dict, titulo=None):
        try:
            fn = f"{REPORTS_PATH}Movimientos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            doc = self._doc_landscape(fn)
            titulo = titulo or "REPORTE DE MOVIMIENTOS"
            els = [
                Paragraph(titulo.upper(), self._titulo_style()),
                Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                          self.styles['Normal']),
                Spacer(1, 0.25*inch),
            ]
            data = [[self._ph(h) for h in
                     ['ID','Producto','Tipo','Cantidad','Fecha','Usuario','Descripción']]]
            for m in movimientos:
                prod = productos_dict.get(m['id_producto'], {})
                prod_nombre = (m.get('nombre_producto')
                               or (prod.get('nombre') if prod else 'N/A'))
                usuario = m.get('usuario_nombre') or m.get('usuario') or 'Sistema'
                desc = (m.get('descripcion') or '')[:50]
                data.append([
                    self._p(m['id']), self._p(prod_nombre),
                    self._p(m.get('tipo_movimiento','')), self._p(m['cantidad']),
                    self._p(m['fecha'].strftime('%d/%m/%Y %H:%M') if m.get('fecha') else ''),
                    self._p(usuario), self._p(desc),
                ])
            cols = [1.2*cm, 5*cm, 2.5*cm, 2*cm, 3.5*cm, 3*cm, 6.5*cm]
            t = Table(data, colWidths=cols, repeatRows=1)
            t.setStyle(self._table_style())
            els.append(t)
            doc.build(els)
            return True, f"Guardado en: {fn}"
        except Exception as e:
            return False, str(e)

    # ── Estadísticas ──────────────────────────────────────────────────────────

    def generar_reporte_estadisticas(self, estadisticas):
        try:
            fn = f"{REPORTS_PATH}Estadisticas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            doc = SimpleDocTemplate(fn, pagesize=letter)
            els = [
                Paragraph("REPORTE DE ESTADÍSTICAS", self._titulo_style()),
                Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                          self.styles['Normal']),
                Spacer(1, 0.3*inch),
            ]
            data = [
                [self._ph('Métrica'), self._ph('Valor')],
                [self._p('Total de Productos'),
                 self._p(estadisticas.get('total_productos', 0))],
                [self._p('Stock Total (Unidades)'),
                 self._p(estadisticas.get('stock_total', 0))],
                [self._p('Valor Total Inventario'),
                 self._p(f"${estadisticas.get('valor_total', 0):.2f}")],
                [self._p('Productos con Stock Bajo/Crítico'),
                 self._p(estadisticas.get('bajo_stock', 0))],
                [self._p('Total de Proveedores'),
                 self._p(estadisticas.get('total_proveedores', 0))],
            ]
            t = Table(data, colWidths=[9*cm, 5*cm])
            t.setStyle(self._table_style())
            els.append(t)
            doc.build(els)
            return True, f"Guardado en: {fn}"
        except Exception as e:
            return False, str(e)
