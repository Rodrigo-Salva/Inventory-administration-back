import contextvars
from typing import Optional

# Definir variables de contexto para almacenar datos de la solicitud actual
# Esto nos permite acceder a esta información en la capa de base de datos
# (SQLAlchemy listeners) donde no tenemos acceso directo al objeto Request o FastAPI Depends

current_user_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "current_user_id", default=None
)

current_tenant_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "current_tenant_id", default=None
)

current_ip_address: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_ip_address", default=None
)

current_user_agent: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_user_agent", default=None
)

def get_current_user_id() -> Optional[int]:
    return current_user_id.get()

def get_current_tenant_id() -> Optional[int]:
    return current_tenant_id.get()

def get_current_ip_address() -> Optional[str]:
    return current_ip_address.get()

def get_current_user_agent() -> Optional[str]:
    return current_user_agent.get()
