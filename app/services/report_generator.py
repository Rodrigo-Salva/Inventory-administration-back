import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

class ReportGenerator:
    @staticmethod
    def generate_sales_summary_pdf(sales, tenant_name: str, filters: dict):
        """
        Genera un reporte PDF resumen de ventas.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Título
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1, # Center
            spaceAfter=12,
            textColor=colors.indigo
        )
        elements.append(Paragraph(f"REPORTE DE VENTAS - {tenant_name.upper()}", title_style))
        
        # Subtítulo con fecha
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1,
            spaceAfter=20,
            textColor=colors.gray
        )
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        elements.append(Paragraph(f"Generado el: {date_str}", subtitle_style))

        # Información de filtros
        filter_text = "Filtros aplicados: "
        filter_parts = []
        if filters.get('start_date'): filter_parts.append(f"Desde: {filters['start_date'].strftime('%d/%m/%Y')}")
        if filters.get('end_date'): filter_parts.append(f"Hasta: {filters['end_date'].strftime('%d/%m/%Y')}")
        if filters.get('status'): filter_parts.append(f"Estado: {filters['status'].upper()}")
        if filters.get('payment_method'): filter_parts.append(f"Pago: {filters['payment_method'].upper()}")
        if filters.get('search'): filter_parts.append(f"Búsqueda: '{filters['search']}'")
        
        if not filter_parts: filter_text += "Ninguno (Historial completo)"
        else: filter_text += ", ".join(filter_parts)
        
        elements.append(Paragraph(filter_text, styles['Normal']))
        elements.append(Spacer(1, 12))

        # Tabla de Datos
        data = [["ID", "Fecha", "Vendedor", "Método", "Estado", "Total"]]
        total_sum = 0
        
        for sale in sales:
            vendedor = sale.user.email.split('@')[0] if sale.user else "N/A"
            total_sum += float(sale.total_amount)
            data.append([
                f"#{sale.id}",
                sale.created_at.strftime("%d/%m/%Y %H:%M"),
                vendedor,
                sale.payment_method.upper(),
                sale.status.upper(),
                f"${float(sale.total_amount):,.2f}"
            ])

        # Fila de Total
        data.append(["", "", "", "", "TOTAL:", f"${total_sum:,.2f}"])

        table = Table(data, colWidths=[40, 100, 80, 80, 80, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.indigo),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('GRID', (0, 0), (-1, -2), 1, colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('ALIGN', (-2, -1), (-1, -1), 'RIGHT'),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.indigo),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.indigo),
        ]))
        
        elements.append(table)
        
        # Generar PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
