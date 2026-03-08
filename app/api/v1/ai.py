from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from ...models import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from ...dependencies import get_current_user, require_permission
from ...services.ai_service import AIService
from ...models.user import User
from pydantic import BaseModel

router = APIRouter()

class DescriptionRequest(BaseModel):
    name: str
    category: Optional[str] = None
    tags: List[str] = []

@router.post("/generate-description")
async def generate_description(
    data: DescriptionRequest,
    current_user: User = Depends(require_permission("products:edit"))
):
    """Genera una descripción para un producto usando IA"""
    ai_service = AIService()
    description = await ai_service.generate_product_description(
        name=data.name,
        category=data.category,
        tags=data.tags
    )
    return {"description": description}

@router.get("/suggest-categories")
async def suggest_categories(
    name: str = Query(...),
    description: str = Query(...),
    current_user: User = Depends(get_current_user)
):
    """Sugiere categorías usando IA"""
    ai_service = AIService()
    categories = await ai_service.suggest_categories(name, description)
    return {"categories": categories}

@router.post("/forecast")
async def get_demand_forecast(
    current_user: User = Depends(require_permission("ai:forecast")),
    db: AsyncSession = Depends(get_db)
):
    """Analiza historial de ventas con IA para predecir demanda"""
    from ...repositories.report_repo import ReportRepository
    
    report_repo = ReportRepository(db)
    sale_history = await report_repo.get_ai_sales_history(current_user.tenant_id)
    
    ai_service = AIService()
    analysis = await ai_service.forecast_demand(sale_history)
    
    return {"analysis": analysis}
