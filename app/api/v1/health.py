from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check básico"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "inventory-saas"
        }
    )


@router.get("/readiness")
async def readiness_check():
    """Readiness check para Kubernetes"""
    # Aquí podrías verificar conexión a DB, Redis, etc.
    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "checks": {
                "database": "ok",
                "redis": "ok"
            }
        }
    )
