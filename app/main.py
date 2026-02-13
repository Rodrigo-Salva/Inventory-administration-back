from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from .core.security import verify_token, create_access_token
from .models.base import get_db
from .dependencies import get_current_tenant
from .api.v1 import auth, products  # Crearemos después

app = FastAPI(title="Inventory SaaS", version="1.0.0")

security = HTTPBearer()

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/v1", tags=["products"])

@app.get("/")
async def root():
    return {"message": "Inventory SaaS API - ¡Listo para SaaS multi-tenant!"}