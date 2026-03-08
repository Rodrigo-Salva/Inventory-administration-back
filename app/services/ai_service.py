import google.generativeai as genai
from typing import Optional, Dict, Any, List
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = settings.google_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
            logger.warning("GOOGLE_API_KEY not found in settings. AI features will be disabled.")

    async def generate_product_description(self, name: str, category: Optional[str] = None, tags: List[str] = []) -> str:
        """Genera una descripción profesional para un producto"""
        if not self.model:
            return "Servicio de IA no configurado."

        prompt = f"""
        Actúa como un experto en marketing y e-commerce. 
        Genera una descripción persuasiva y profesional para el siguiente producto:
        Nombre: {name}
        Categoría: {category if category else 'General'}
        Etiquetas: {', '.join(tags)}
        
        La descripción debe ser concisa (máximo 3 párrafos), resaltar beneficios y ser atractiva para clientes.
        Responde solo con la descripción, en español.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generando descripción: {e}")
            return f"Error al generar descripción: {str(e)}"

    async def suggest_categories(self, name: str, description: str) -> List[str]:
        """Sugiere categorías basadas en el nombre y descripción"""
        if not self.model:
            return []

        prompt = f"""
        Basado en el producto '{name}' y su descripción '{description}', 
        sugiere las 3 categorías más relevantes para organizarlo en un inventario.
        Responde solo con una lista separada por comas.
        """
        
        try:
            response = self.model.generate_content(prompt)
            categories = [c.strip() for c in response.text.split(',')]
            return categories[:3]
        except Exception as e:
            logger.error(f"Error sugiriendo categorías: {e}")
            return []
            
    async def forecast_demand(self, sale_history: List[Dict[str, Any]]) -> str:
        """Analiza tendencias de venta y predice demanda usando Gemini"""
        if not self.model:
            return "Servicio de IA no configurado."

        prompt = f"""
        Eres un analista experto en cadena de suministro e inventarios. 
        Analiza el historial de ventas de los últimos 60 días para predecir la demanda y recomendar compras prioritarias.
        
        Datos del inventario y ventas:
        {sale_history}
        
        Tu objetivo es:
        1. Identificar los 3 productos con más riesgo de quiebre de stock basado en su ritmo de venta.
        2. Recomendar cantidades específicas para reponer si el stock está por debajo del mínimo o bajando rápido.
        3. detectar productos "muertos" (con stock pero sin ventas).
        4. Dar una recomendación estratégica general para el próximo mes.
        
        Respuesta en ESPAÑOL. Usa un tono profesional y directo. 
        Usa formato Markdown con viñetas y negritas para resaltar puntos clave.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error en predicción de demanda: {e}")
            return "Error al analizar la demanda con IA."
