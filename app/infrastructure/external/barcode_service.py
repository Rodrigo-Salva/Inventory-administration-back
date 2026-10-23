import io
import base64
import barcode
from barcode.writer import ImageWriter
import qrcode
from typing import Optional

class BarcodeService:
    """
    Servicio especializado en la generación de representaciones visuales
    de códigos de barras y QR para productos.
    """

    @staticmethod
    def generate_barcode_base64(data: str, code_type: str = "code128") -> str:
        """
        Genera un código de barras y lo devuelve como una cadena Base64.
        """
        try:
            # Obtener el tipo de barcode solicitado
            barcode_class = barcode.get_barcode_class(code_type)
            
            # Crear el barcode con el escritor de imágenes
            rv = io.BytesIO()
            writer = ImageWriter()
            writer.set_options({
                'module_height': 15.0,
                'font_size': 10,
                'text_distance': 4.0,
            })
            
            my_barcode = barcode_class(data, writer=writer)
            my_barcode.write(rv)
            
            # Convertir a Base64
            base64_str = base64.b64encode(rv.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{base64_str}"
        except Exception as e:
            # Fallback o manejo de error (podemos loguear aquí)
            raise ValueError(f"Error generando barcode: {str(e)}")

    @staticmethod
    def generate_qr_base64(data: str) -> str:
        """
        Genera un código QR y lo devuelve como una cadena Base64.
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            
            base64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{base64_str}"
        except Exception as e:
            raise ValueError(f"Error generando QR: {str(e)}")
