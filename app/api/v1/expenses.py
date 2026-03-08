from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from ...models.user import User
from ...models import get_db
from ...dependencies import require_permission, get_current_tenant
from ...repositories.expense_repo import ExpenseRepository
from ...schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseOut, ExpenseStats, PaginatedExpenses
from datetime import datetime, timedelta

router = APIRouter()

@router.get("", response_model=PaginatedExpenses)
async def list_expenses(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = Query(None, min_length=1),
    current_user: User = Depends(require_permission("expenses:view")),
    db: AsyncSession = Depends(get_db)
):
    repo = ExpenseRepository(db)
    skip = (page - 1) * size
    expenses, total = await repo.get_by_tenant(
        current_user.tenant_id, 
        skip=skip, 
        limit=size,
        category=category,
        start_date=start_date,
        end_date=end_date,
        search=search
    )
    
    return {
        "items": expenses,
        "total": total,
        "page": page,
        "size": size
    }

@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_in: ExpenseCreate,
    current_user: User = Depends(require_permission("expenses:manage")),
    db: AsyncSession = Depends(get_db)
):
    repo = ExpenseRepository(db)
    expense_data = expense_in.model_dump()
    expense_data["tenant_id"] = current_user.tenant_id
    
    expense = await repo.create(expense_data, user_id=current_user.id)
    await db.commit()
    await db.refresh(expense)
    return expense

@router.get("/stats", response_model=ExpenseStats)
async def get_expense_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_permission("expenses:view")),
    db: AsyncSession = Depends(get_db)
):
    repo = ExpenseRepository(db)
    stats = await repo.get_stats(current_user.tenant_id, days=days)
    return stats

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    id: int,
    current_user: User = Depends(require_permission("expenses:manage")),
    db: AsyncSession = Depends(get_db)
):
    repo = ExpenseRepository(db)
    expense = await repo.get_by_id(id, current_user.tenant_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
        
    await repo.delete(id, current_user.tenant_id, user_id=current_user.id)
    await db.commit()
    return None
