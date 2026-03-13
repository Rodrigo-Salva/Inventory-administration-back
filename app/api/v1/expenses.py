from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from ...models.base import get_db
from ...models.user import User
from ...dependencies import get_current_user, get_current_tenant
from ...schemas.expense import (
    ExpenseCreate, ExpenseResponse, ExpenseCategoryCreate, 
    ExpenseCategoryResponse, ExpenseSummary
)
from ...repositories.expense_repo import ExpenseRepository

router = APIRouter(tags=["Expenses"])

# --- Categorías ---

@router.post("/categories", response_model=ExpenseCategoryResponse)
async def create_category(
    category_in: ExpenseCategoryCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = ExpenseRepository(db)
    return await repo.create_category(tenant_id, category_in.name, category_in.description)

@router.get("/categories", response_model=List[ExpenseCategoryResponse])
async def list_categories(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = ExpenseRepository(db)
    return await repo.get_categories(tenant_id)

# --- Gastos ---

@router.post("/", response_model=ExpenseResponse)
async def create_expense(
    expense_in: ExpenseCreate,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ExpenseRepository(db)
    return await repo.create_expense(tenant_id, current_user.id, expense_in)

@router.get("/", response_model=ExpenseSummary)
async def list_expenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    cash_session_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = ExpenseRepository(db)
    items, total = await repo.get_expenses_paginated(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        cash_session_id=cash_session_id
    )
    return ExpenseSummary(items=items, total=total, page=page, size=page_size)
