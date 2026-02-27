import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, gray
from datetime import datetime

class TicketGenerator:
    @staticmethod
    def generate_ticket(sale, tenant_name: str):
        """
        Genera un ticket de venta en PDF estilo recibo de 80mm.
        """
        # Ancho típico de ticket: 80mm
        width = 80 * mm
        # El alto depende de la cantidad de ítems, empezamos con algo base
        item_count = len(sale.items)
        height = (100 + (item_count * 15)) * mm
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(width, height))
        
        # Invertimos coordenadas para escribir de arriba hacia abajo
        curr_y = height - 10 * mm
        
        # Header - Empresa
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width/2, curr_y, tenant_name.upper())
        curr_y -= 8 * mm
        
        c.setFont("Helvetica", 9)
        c.drawCentredString(width/2, curr_y, "COMPROBANTE DE VENTA")
        curr_y -= 5 * mm
        
        # Info Venta
        c.setDash(1, 2)
        c.line(5*mm, curr_y, width-5*mm, curr_y)
        c.setDash()
        curr_y -= 6 * mm
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(5*mm, curr_y, f"ORDEN: #{sale.id}")
        curr_y -= 5 * mm
        
        c.setFont("Helvetica", 8)
        c.drawString(5*mm, curr_y, f"FECHA: {sale.created_at.strftime('%d/%m/%Y %H:%M')}")
        curr_y -= 5 * mm
        
        # Tabla de ítems
        curr_y -= 4 * mm
        c.setFont("Helvetica-Bold", 8)
        c.drawString(5*mm, curr_y, "PRODUCTO")
        c.drawRightString(width-5*mm, curr_y, "TOTAL")
        curr_y -= 4 * mm
        
        c.line(5*mm, curr_y, width-5*mm, curr_y)
        curr_y -= 6 * mm
        
        c.setFont("Helvetica", 8)
        for item in sale.items:
            # Nombre del producto y cantidad
            name = item.product.name[:25]
            qty_price = f"{item.quantity} x ${float(item.unit_price):,.2f}"
            
            c.setFont("Helvetica-Bold", 8)
            c.drawString(5*mm, curr_y, name.upper())
            c.setFont("Helvetica", 8)
            c.drawRightString(width-5*mm, curr_y, f"${float(item.subtotal):,.2f}")
            curr_y -= 4 * mm
            c.setFont("Helvetica", 7)
            c.drawString(5*mm, curr_y, qty_price)
            curr_y -= 8 * mm
            
            # Si nos quedamos sin espacio (poco probable para tickets cortos)
            if curr_y < 15*mm:
                c.showPage()
                curr_y = height - 15*mm

        # Totales
        c.setDash(1, 2)
        c.line(5*mm, curr_y, width-5*mm, curr_y)
        c.setDash()
        curr_y -= 10 * mm
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(5*mm, curr_y, "TOTAL:")
        c.drawRightString(width-5*mm, curr_y, f"${float(sale.total_amount):,.2f}")
        curr_y -= 8 * mm
        
        c.setFont("Helvetica", 8)
        c.drawString(5*mm, curr_y, f"PAGO: {sale.payment_method.upper()}")
        curr_y -= 15 * mm
        
        # Footer
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(width/2, curr_y, "¡Gracias por su compra!")
        curr_y -= 5 * mm
        c.drawCentredString(width/2, curr_y, "Inventory SaaS PRO")
        
        c.save()
        buffer.seek(0)
        return buffer
