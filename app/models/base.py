"""Compatibilidad temporal para modelos heredados.

Los nuevos módulos deben importar desde :mod:`app.shared.infrastructure.database`.
Este archivo se mantiene mientras los modelos existentes se migran de forma
incremental, evitando cambios masivos de una sola vez.
"""

from app.shared.infrastructure.database import (
    Base,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    async_session,
    engine,
    get_db,
)

__all__ = [
    "Base",
    "SoftDeleteMixin",
    "TenantMixin",
    "TimestampMixin",
    "async_session",
    "engine",
    "get_db",
]
