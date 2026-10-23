from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.cash_dto import AdjustLoyaltyPointsCommand, UpdateLoyaltyConfigCommand
from app.application.sales.cash_use_cases import AdjustLoyaltyPoints, UpdateLoyaltyConfig
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User
from app.infrastructure.persistence.repositories.sales.loyalty_repo import LoyaltyRepository
from app.presentation.api.v1.sales.cash_deps import get_adjust_loyalty_points, get_update_loyalty_config
from app.presentation.dependencies import get_current_tenant, require_permission
from app.presentation.schemas.sales.loyalty import (
    LoyaltyConfig,
    LoyaltyConfigUpdate,
    LoyaltyTransaction,
    LoyaltyTransactionCreate,
)

router = APIRouter()


@router.get("/config", response_model=LoyaltyConfig)
async def get_loyalty_config(
    db: AsyncSession = Depends(get_db), tenant_id: int = Depends(get_current_tenant)
):
    """Configuración de lealtad (la consume el POS para calcular descuentos)"""
    return await LoyaltyRepository(db).get_config(tenant_id)


@router.put("/config", response_model=LoyaltyConfig)
async def update_loyalty_config(
    update_data: LoyaltyConfigUpdate,
    use_case: UpdateLoyaltyConfig = Depends(get_update_loyalty_config),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("settings:manage")),
):
    """Actualiza las reglas del programa de lealtad (requiere 'settings:manage')"""
    await use_case.execute(
        UpdateLoyaltyConfigCommand(current_user.tenant_id, update_data.model_dump(exclude_unset=True))
    )
    return await LoyaltyRepository(db).get_config(current_user.tenant_id)


@router.get("/transactions/{customer_id}", response_model=List[LoyaltyTransaction])
async def get_customer_loyalty_transactions(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("customers:view")),
):
    return await LoyaltyRepository(db).get_customer_transactions(current_user.tenant_id, customer_id)


@router.post("/transactions", response_model=LoyaltyTransaction)
async def add_loyalty_transaction(
    trans_data: LoyaltyTransactionCreate,
    use_case: AdjustLoyaltyPoints = Depends(get_adjust_loyalty_points),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("customers:edit")),
):
    """Ajuste manual de puntos de un cliente (requiere 'customers:edit'; siempre se registra como 'adjust')"""
    transaction_id = await use_case.execute(
        AdjustLoyaltyPointsCommand(
            current_user.tenant_id, trans_data.customer_id, trans_data.points,
            trans_data.description, trans_data.sale_id,
        )
    )
    return await LoyaltyRepository(db).get_transaction(transaction_id, current_user.tenant_id)
