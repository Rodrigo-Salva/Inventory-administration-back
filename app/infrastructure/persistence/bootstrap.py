"""Datos de referencia al arrancar (SOLO datos; el esquema lo gestiona Alembic: `alembic upgrade head`).

Es idempotente y cada paso corre en un SAVEPOINT: un fallo se registra y no aborta el arranque.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.infrastructure.persistence.defaults import DEFAULT_BRANCH_NAME, DEFAULT_EXPENSE_CATEGORIES
from app.infrastructure.persistence.permissions_catalog import PERMISSIONS

logger = logging.getLogger(__name__)

UPSERT_PERMISSION = """
    INSERT INTO permissions (name, codename, module) VALUES (:name, :codename, :module)
    ON CONFLICT (codename) DO UPDATE SET module = EXCLUDED.module, name = EXCLUDED.name
"""

ENSURE_DEFAULT_BRANCH = """
    INSERT INTO branches (tenant_id, name, is_active, is_deleted, created_at, updated_at)
    SELECT t.id, :name, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    FROM tenants t
    WHERE NOT EXISTS (SELECT 1 FROM branches b WHERE b.tenant_id = t.id AND b.is_deleted = false)
"""

async def _safely(conn: AsyncConnection, sql: str, params: dict | None = None) -> None:
    try:
        async with conn.begin_nested():
            await conn.execute(text(sql), params or {})
    except Exception as error:
        logger.warning("Paso de arranque omitido (%s): %s", " ".join(sql.split())[:70], error)


async def bootstrap_reference_data(conn: AsyncConnection) -> None:
    for name, codename, module in PERMISSIONS:
        await _safely(conn, UPSERT_PERMISSION, {"name": name, "codename": codename, "module": module})
    await _safely(conn, ENSURE_DEFAULT_BRANCH, {"name": DEFAULT_BRANCH_NAME})
    # un único INSERT por categoría: la guarda "no tiene ninguna" se evalúa antes de insertar la primera
    existing = (await conn.execute(text("SELECT tenant_id FROM expense_categories GROUP BY tenant_id"))).scalars().all()
    for name, description in DEFAULT_EXPENSE_CATEGORIES:
        await _safely(
            conn,
            "INSERT INTO expense_categories (tenant_id, name, description, is_active, created_at, updated_at) "
            "SELECT t.id, :name, :description, true, NOW(), NOW() FROM tenants t "
            "WHERE t.id <> ALL(CAST(:existing AS integer[]))",
            {"name": name, "description": description, "existing": list(existing) or [0]},
        )
    logger.info("Datos de referencia listos (%d permisos)", len(PERMISSIONS))
