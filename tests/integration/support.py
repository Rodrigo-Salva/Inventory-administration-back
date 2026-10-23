"""Helpers de integración: base PostgreSQL de PRUEBAS, SQL síncrono y Alembic en subproceso.

* El esquema se construye con las MIGRACIONES REALES (`alembic upgrade head`), así que cada corrida
  también prueba que las migraciones funcionan sobre una base vacía.
* Seguridad: se rechaza cualquier base cuyo nombre no termine en `_test` (se vacía en cada prueba)
  y se omite todo si no hay conexión.
"""

import os
import subprocess
import sys
from pathlib import Path

import psycopg2
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.config import settings

ROOT = Path(__file__).resolve().parents[2]

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    base_url, _, database_name = settings.database_url.rpartition("/")
    TEST_DATABASE_URL = f"{base_url}/{database_name}_test"

SYNC_DSN = TEST_DATABASE_URL.replace("postgresql+asyncpg", "postgresql")


def assert_is_test_database() -> None:
    name = TEST_DATABASE_URL.rpartition("/")[2].split("?")[0]
    if not name.endswith("_test"):
        raise RuntimeError(f"Se rechaza la base '{name}': las pruebas de integración exigen un nombre *_test")


def database_available() -> bool:
    try:
        psycopg2.connect(SYNC_DSN, connect_timeout=3).close()
        return True
    except Exception:
        return False


def sql(statement: str, params=None, fetch: bool = False):
    """Ejecuta SQL síncrono contra la base de pruebas (para preparar y verificar datos)."""
    assert_is_test_database()
    with psycopg2.connect(SYNC_DSN) as conn, conn.cursor() as cur:
        cur.execute(statement, params)
        return cur.fetchall() if fetch else None


def reset_schema() -> None:
    assert_is_test_database()
    sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")


def alembic(*args: str) -> subprocess.CompletedProcess:
    """Ejecuta Alembic contra la base de pruebas en un subproceso."""
    assert_is_test_database()
    return subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "alembic", *args],
        cwd=ROOT, env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        capture_output=True, text=True,
    )


def migrate_to_head() -> None:
    reset_schema()
    result = alembic("upgrade", "head")
    assert result.returncode == 0, f"alembic upgrade head falló:\n{result.stderr[-2000:]}"
    # datos de referencia (permisos) como en el arranque real
    import asyncio

    from app.infrastructure.persistence.bootstrap import bootstrap_reference_data

    async def seed():
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        async with engine.begin() as conn:
            await bootstrap_reference_data(conn)
        await engine.dispose()

    asyncio.run(seed())


def ensure_migrated() -> None:
    """Deja la base migrada y sin datos de negocio (conserva permisos y alembic_version)."""
    assert_is_test_database()
    if not sql("SELECT to_regclass('public.alembic_version')", fetch=True)[0][0]:
        migrate_to_head()
        return
    tables = [r[0] for r in sql(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
        "AND tablename NOT IN ('alembic_version', 'permissions')", fetch=True)]
    if tables:
        sql("TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " RESTART IDENTITY CASCADE")
