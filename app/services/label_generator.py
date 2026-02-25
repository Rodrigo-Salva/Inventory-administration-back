import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.lib.colors import black

class LabelGenerator:
    @staticmethod
    def generate_pdf(products, labels_per_row=3, rows_per_page=8):
        """
        Generates a PDF with product labels.
        Each label contains: Name, SKU, Price, and a QR code (using Barcode or SKU).
        """
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        page_width, page_height = A4

        # Margins and layout settings
        margin_x = 10 * mm
        margin_y = 10 * mm
        gap_x = 5 * mm
        gap_y = 5 * mm

        label_width = (page_width - 2 * margin_x - (labels_per_row - 1) * gap_x) / labels_per_row
        label_height = (page_height - 2 * margin_y - (rows_per_page - 1) * gap_y) / rows_per_page

        x_pos = margin_x
        y_pos = page_height - margin_y - label_height

        count = 0
        for product in products:
            # Draw label border (delicate light gray)
            c.setStrokeColorRGB(0.9, 0.9, 0.9)
            c.setLineWidth(0.1)
            c.roundRect(x_pos, y_pos, label_width, label_height, 2*mm)

            # Product Name
            c.setFillColor(black)
            c.setFont("Helvetica-Bold", 9)
            name_text = product.name[:35] + ("..." if len(product.name) > 35 else "")
            c.drawString(x_pos + 3*mm, y_pos + label_height - 5*mm, name_text)

            # SKU
            c.setFont("Helvetica", 7)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawString(x_pos + 3*mm, y_pos + label_height - 9*mm, f"SKU: {product.sku}")

            # Price
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(black)
            price_str = f"${float(product.price):,.2f}"
            c.drawString(x_pos + 3*mm, y_pos + 5*mm, price_str)

            # QR Code
            qr_data = product.barcode if product.barcode else product.sku
            qr_code = qr.QrCodeWidget(qr_data)
            qr_code.barFillColor = black
            
            bounds = qr_code.getBounds()
            qr_w = bounds[2] - bounds[0]
            qr_h = bounds[3] - bounds[1]
            
            # Target size for QR
            size = min(label_height * 0.5, label_width * 0.35)
            
            d = Drawing(size, size, transform=[size/qr_w, 0, 0, size/qr_h, 0, 0])
            d.add(qr_code)
            
            renderPDF.draw(d, c, x_pos + label_width - size - 2*mm, y_pos + 2*mm)

            # Update positions
            count += 1
            if count % labels_per_row == 0:
                x_pos = margin_x
                y_pos -= (label_height + gap_y)
            else:
                x_pos += (label_width + gap_x)

            # New page if needed
            if count % (labels_per_row * rows_per_page) == 0 and count < len(products):
                c.showPage()
                x_pos = margin_x
                y_pos = page_height - margin_y - label_height

        c.save()
        buffer.seek(0)
        return buffer
