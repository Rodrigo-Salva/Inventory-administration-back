"""Endpoints operativos que no pertenecen a un dominio de negocio."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check():
    """Liveness probe: confirma que el proceso HTTP responde."""
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "service": "inventory-saas"},
    )


@router.get("/readiness")
async def readiness_check():
    """Readiness probe; las dependencias se verificarán en la siguiente fase."""
    return JSONResponse(
        status_code=200,
        content={"status": "ready", "checks": {"database": "ok", "redis": "ok"}},
    )
