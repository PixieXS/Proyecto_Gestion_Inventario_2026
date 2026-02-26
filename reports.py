from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from datetime import datetime
import os
from config import REPORTS_PATH

class ReportGenerator:
    """Generador de reportes en PDF"""
    
    def __init__(self):
        if not os.path.exists(REPORTS_PATH):
            os.makedirs(REPORTS_PATH)
        self.styles = getSampleStyleSheet()
    
    def generar_reporte_inventario(self, productos):
        """Generar reporte de inventario"""
        try:
            filename = f"{REPORTS_PATH}Inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            doc = SimpleDocTemplate(filename, pagesize=letter)
            elements = []
            
            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=self.styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=30,
                alignment=1
            )
            elements.append(Paragraph("REPORTE DE INVENTARIO", title_style))
            elements.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", self.styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))
            
            # Tabla de datos
            table_data = [['ID', 'Producto', 'Descripción', 'Cantidad', 'Precio Unitario', 'Proveedor']]
            
            for producto in productos:
                table_data.append([
                    str(producto['id']),
                    producto['nombre'],
                    producto['descripcion'][:30] if producto['descripcion'] else '',
                    str(producto['cantidad']),
                    f"${float(producto['precio_unitario']):.2f}",
                    producto['proveedor'] if producto['proveedor'] else 'N/A'
                ])
            
            table = Table(table_data, colWidths=[0.5*inch, 1.5*inch, 1.5*inch, 0.8*inch, 1.2*inch, 1.2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
            ]))
            
            elements.append(table)
            
            # Crear PDF
            doc.build(elements)
            return True, f"Reporte guardado en: {filename}"
        except Exception as e:
            return False, f"Error al generar reporte: {e}"
    
    def generar_reporte_movimientos(self, movimientos, productos_dict):
        """Generar reporte de movimientos de inventario"""
        try:
            filename = f"{REPORTS_PATH}Movimientos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            doc = SimpleDocTemplate(filename, pagesize=letter)
            elements = []
            
            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=self.styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=30,
                alignment=1
            )
            elements.append(Paragraph("REPORTE DE MOVIMIENTOS", title_style))
            elements.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", self.styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))
            
            # Tabla de datos
            table_data = [['ID Mov', 'Producto', 'Tipo', 'Cantidad', 'Fecha', 'Descripción']]
            
            for movimiento in movimientos:
                producto_nombre = productos_dict.get(movimiento['id_producto'], {}).get('nombre', 'N/A')
                table_data.append([
                    str(movimiento['id']),
                    producto_nombre,
                    movimiento['tipo_movimiento'],
                    str(movimiento['cantidad']),
                    movimiento['fecha'].strftime('%d/%m/%Y %H:%M') if movimiento['fecha'] else '',
                    movimiento['descripcion'][:20] if movimiento['descripcion'] else ''
                ])
            
            table = Table(table_data, colWidths=[0.6*inch, 1.8*inch, 1*inch, 1*inch, 1.2*inch, 1.2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
            ]))
            
            elements.append(table)
            doc.build(elements)
            return True, f"Reporte guardado en: {filename}"
        except Exception as e:
            return False, f"Error al generar reporte: {e}"
    
    def generar_reporte_estadisticas(self, estadisticas):
        """Generar reporte de estadísticas"""
        try:
            filename = f"{REPORTS_PATH}Estadisticas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            doc = SimpleDocTemplate(filename, pagesize=letter)
            elements = []
            
            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=self.styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=30,
                alignment=1
            )
            elements.append(Paragraph("REPORTE DE ESTADÍSTICAS", title_style))
            elements.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", self.styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))
            
            # Tabla de estadísticas
            table_data = [
                ['Métrica', 'Valor'],
                ['Total de Productos', str(estadisticas.get('total_productos', 0))],
                ['Stock Total (Unidades)', str(estadisticas.get('stock_total', 0))],
                ['Valor Total Inventario', f"${estadisticas.get('valor_total', 0):.2f}"],
                ['Productos con Stock Bajo', str(estadisticas.get('bajo_stock', 0))]
            ]
            
            table = Table(table_data, colWidths=[3*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
            ]))
            
            elements.append(table)
            doc.build(elements)
            return True, f"Reporte guardado en: {filename}"
        except Exception as e:
            return False, f"Error al generar reporte: {e}"
