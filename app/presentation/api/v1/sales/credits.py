from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User
from app.presentation.dependencies import get_current_user, require_permission
from app.infrastructure.persistence.repositories.sales.credit_repo import CreditRepository
from app.infrastructure.persistence.repositories.sales.payment_repo import PaymentRepository
from app.application.sales.cash_dto import RegisterCreditPaymentCommand
from app.application.sales.cash_use_cases import RegisterCreditPayment
from app.presentation.api.v1.sales.cash_deps import get_register_credit_payment
from app.presentation.schemas.sales.credit import CreditOut, CreditSummary, PaymentCreate, PaymentOut

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
    from app.infrastructure.persistence.models.sales.credit import Credit
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
    use_case: RegisterCreditPayment = Depends(get_register_credit_payment),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("pos:sales"))
):
    """Registra un abono a un crédito"""
    payment_id = await use_case.execute(
        RegisterCreditPaymentCommand(
            tenant_id=current_user.tenant_id,
            credit_id=payment_in.credit_id,
            amount=payment_in.amount,
            payment_method=getattr(payment_in.payment_method, "value", payment_in.payment_method),
            notes=payment_in.notes,
        )
    )
    return await PaymentRepository(db).get_by_id(payment_id, current_user.tenant_id)
