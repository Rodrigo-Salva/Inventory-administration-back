"""Endpoints operativos que no pertenecen a un dominio de negocio."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.database import get_db
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("")  # GET /health (lo usa el HEALTHCHECK de Docker)
@router.get("/health", include_in_schema=False)  # alias histórico: GET /health/health
async def health_check():
    """Liveness probe: confirma que el proceso HTTP responde."""
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "service": "inventory-saas"},
    )


@router.get("/readiness")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness probe: verifica de verdad la conexión a la base de datos."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "checks": {"database": "down"}},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ready", "checks": {"database": "ok"}},
    )
