from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ...models.base import get_db
from app.modules.identity.infrastructure.persistence.models.user import User
from ...dependencies import get_current_user, require_permission
from ...repositories.credit_repo import CreditRepository
from ...repositories.payment_repo import PaymentRepository
from ...schemas.credit import CreditOut, CreditSummary, PaymentCreate, PaymentOut

router = APIRouter()

@router.get("/customer/{customer_id}", response_model=List[CreditSummary])
async def get_customer_credits(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("customers:view"))
):
    """Obtiene todos los créditos de un cliente"""
    repo = CreditRepository(db)
    return await repo.get_by_customer(current_user.tenant_id, customer_id)

@router.get("/{credit_id}", response_model=CreditOut)
async def get_credit_detail(
    credit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("customers:view"))
):
    """Obtiene el detalle de un crédito específico incluyendo sus pagos"""
    from sqlalchemy.orm import selectinload
    from ...models.credit import Credit
    from sqlalchemy import select, and_
    
    query = select(Credit).options(
        selectinload(Credit.payments)
    ).where(
        and_(Credit.id == credit_id, Credit.tenant_id == current_user.tenant_id)
    )
    
    result = await db.execute(query)
    credit = result.scalar_one_or_none()
    
    if not credit:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")
        
    return credit

@router.post("/pay", response_model=PaymentOut)
async def register_credit_payment(
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("pos:sales"))
):
    """Registra un abono a un crédito"""
    repo = PaymentRepository(db)
    try:
        payment = await repo.register_payment(
            tenant_id=current_user.tenant_id,
            credit_id=payment_in.credit_id,
            amount=payment_in.amount,
            payment_method=payment_in.payment_method,
            notes=payment_in.notes
        )
        await db.commit()
        return payment
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
