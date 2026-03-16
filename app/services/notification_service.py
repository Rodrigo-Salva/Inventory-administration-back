import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from ..core.config import settings
from ..core.logging_config import get_logger

logger = get_logger(__name__)

class NotificationService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("SMTP_FROM", self.smtp_user)

    async def send_email(self, to_email: str, subject: str, body: str, is_html: bool = True):
        """Envía un correo electrónico de forma sincrónica (ejecutar en BackgroundTasks)"""
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP no configurado. No se enviará el correo.")
            return False

        msg = MIMEMultipart()
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg["Subject"] = subject

        part = MIMEText(body, "html" if is_html else "plain")
        msg.attach(part)

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            logger.info(f"Correo enviado exitosamente a {to_email}")
            return True
        except Exception as e:
            logger.error(f"Error enviando correo: {str(e)}")
            return False

    def get_stock_alert_template(self, product_name: str, current_stock: int, threshold: int) -> str:
        """Genera una plantilla HTML para alertas de stock bajo"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #d9534f;">⚠️ Alerta de Stock Bajo</h2>
                    <p>Hola,</p>
                    <p>El siguiente producto ha alcanzado su nivel crítico de inventario:</p>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Producto:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{product_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Stock Actual:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; color: #d9534f;">{current_stock}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Umbral Configurado:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{threshold}</td>
                        </tr>
                    </table>
                    <p style="margin-top: 20px;">Por favor, realiza un pedido a tu proveedor lo antes posible.</p>
                    <hr style="border: 0; border-top: 1px solid #eee;">
                    <p style="font-size: 12px; color: #999;">Este es un mensaje automático de Inventory SaaS.</p>
                </div>
            </body>
        </html>
        """
