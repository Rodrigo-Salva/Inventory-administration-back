from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from ..models.expense import Expense, ExpenseCategory
from typing import List, Optional, Tuple
from datetime import datetime

class ExpenseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_category(self, tenant_id: int, name: str, description: Optional[str] = None) -> ExpenseCategory:
        category = ExpenseCategory(tenant_id=tenant_id, name=name, description=description)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def get_categories(self, tenant_id: int) -> List[ExpenseCategory]:
        result = await self.db.execute(
            select(ExpenseCategory).where(ExpenseCategory.tenant_id == tenant_id, ExpenseCategory.is_active == True)
        )
        categories = list(result.scalars().all())
        
        # Fallback: Si no hay categorías, crear las básicas on-the-fly
        if not categories:
            default_categories = [
                ('Servicios Públicos', 'Pago de luz, agua, internet, etc.'),
                ('Arriendo', 'Pago de alquiler del local'),
                ('Suministros', 'Papelería, limpieza, etc.'),
                ('Pago a Proveedores', 'Pagos directos a proveedores de mercancía'),
                ('Otros', 'Gastos varios no clasificados')
            ]
            for name, desc in default_categories:
                new_cat = ExpenseCategory(tenant_id=tenant_id, name=name, description=desc, is_active=True)
                self.db.add(new_cat)
            
            await self.db.commit()
            
            # Re-consultar
            result = await self.db.execute(
                select(ExpenseCategory).where(ExpenseCategory.tenant_id == tenant_id, ExpenseCategory.is_active == True)
            )
            categories = list(result.scalars().all())

        return categories

    async def create_expense(self, tenant_id: int, user_id: int, expense_data) -> Expense:
        new_expense = Expense(
            tenant_id=tenant_id,
            user_id=user_id,
            category_id=expense_data.category_id,
            cash_session_id=expense_data.cash_session_id,
            amount=expense_data.amount,
            description=expense_data.description,
            expense_date=expense_data.expense_date or datetime.utcnow()
        )
        self.db.add(new_expense)
        await self.db.commit()
        
        # Recargar con la categoría para evitar error de MissingGreenlet en la respuesta
        result = await self.db.execute(
            select(Expense)
            .options(selectinload(Expense.category))
            .where(Expense.id == new_expense.id)
        )
        return result.scalar_one()

    async def get_expenses_paginated(
        self, 
        tenant_id: int, 
        page: int = 1, 
        page_size: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_id: Optional[int] = None,
        cash_session_id: Optional[int] = None
    ) -> Tuple[List[Expense], int]:
        query = select(Expense).options(selectinload(Expense.category)).where(Expense.tenant_id == tenant_id)
        
        if start_date:
            query = query.where(Expense.expense_date >= start_date)
        if end_date:
            query = query.where(Expense.expense_date <= end_date)
        if category_id:
            query = query.where(Expense.category_id == category_id)
        if cash_session_id:
            query = query.where(Expense.cash_session_id == cash_session_id)
            
        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        # Paginación y orden
        query = query.order_by(Expense.expense_date.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        
        return list(result.scalars().all()), total or 0

    async def get_total_expenses_by_session(self, tenant_id: int, cash_session_id: int) -> float:
        result = await self.db.execute(
            select(func.sum(Expense.amount)).where(
                Expense.tenant_id == tenant_id, 
                Expense.cash_session_id == cash_session_id
            )
        )
        return float(result.scalar() or 0)
