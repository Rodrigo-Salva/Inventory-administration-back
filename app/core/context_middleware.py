import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from .context import current_user_id, current_tenant_id, current_ip_address, current_user_agent
from ..core.security import verify_token

logger = logging.getLogger(__name__)

class ContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Obtener IP y User-Agent
        ip = request.client.host if request.client else "Unknown"
        user_agent = request.headers.get("user-agent", "Unknown")
        
        # 2. Configurar variables base del request
        current_ip_address.set(ip)
        current_user_agent.set(user_agent)
        
        # 3. Intentar obtener el usuario y tenant del token JWT si existe
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                payload = verify_token(token)
                
                # Asignar a contextvars
                current_user_id.set(payload.get("user_id"))
                current_tenant_id.set(payload.get("tenant_id"))
            except Exception as e:
                # Si el token es inválido o expiró, lo ignoramos a nivel de contexto
                # La capa de dependencias (dependencies.py) se encargará de rechazarlo
                logger.debug(f"Error al decodificar token en middleware: {e}")
        
        # 4. Continuar con la petición
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Opcional: Agregar header de tiempo de procesamiento
        response.headers["X-Process-Time"] = str(process_time)
        return response
