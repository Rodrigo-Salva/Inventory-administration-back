"""Limitador de peticiones compartido (slowapi)."""

from pathlib import Path

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.infrastructure.config import settings

# slowapi lee por su cuenta el ".env" del directorio actual con la codificacion del sistema (cp1252 en
# Windows) y falla si contiene tildes. Se le da un archivo vacio propio: la configuracion real la carga
# `settings` (pydantic-settings, UTF-8).
_EMPTY_ENV = str(Path(__file__).with_name("slowapi_empty.env"))

limiter = Limiter(
    key_func=get_remote_address,
    config_filename=_EMPTY_ENV,
    enabled=settings.rate_limit_enabled,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)

AUTH_LIMIT = settings.auth_rate_limit
