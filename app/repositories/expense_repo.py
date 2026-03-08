from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.expense import Expense
from .base_repository import BaseRepository

class ExpenseRepository(BaseRepository[Expense]):
    def __init__(self, db: AsyncSession):
        super().__init__(Expense, db)

    async def get_by_tenant(
        self, 
        tenant_id: int, 
        skip: int = 0, 
        limit: int = 100,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None
    ) -> (List[Expense], int):
        from sqlalchemy import or_
        query = select(Expense).where(Expense.tenant_id == tenant_id)
        
        if category:
            query = query.where(Expense.category == category)
        if start_date:
            query = query.where(Expense.date >= start_date)
        if end_date:
            query = query.where(Expense.date <= end_date)
        if search:
            search_filter = f"%{search}%"
            query = query.where(or_(
                Expense.description.ilike(search_filter),
                Expense.reference.ilike(search_filter)
            ))
            
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.execute(count_query)
        total_count = total.scalar() or 0
        
        # Apply pagination and sorting
        query = query.order_by(desc(Expense.date)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all(), total_count

    async def get_stats(self, tenant_id: int, days: int = 30) -> Dict[str, Any]:
        """Obtiene estadísticas de gastos por categoría y series temporales"""
        from datetime import datetime, timedelta
        from sqlalchemy import cast, Date
        
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        # 1. Totales por categoría
        cat_query = select(
            Expense.category,
            func.sum(Expense.amount).label("total")
        ).where(and_(
            Expense.tenant_id == tenant_id,
            Expense.date >= start_date
        )).group_by(Expense.category)
        
        cat_result = await self.db.execute(cat_query)
        category_totals = {row.category: float(row.total) for row in cat_result.all()}
        
        # 2. Serie temporal diaria
        daily_query = select(
            cast(Expense.date, Date).label("day"),
            func.sum(Expense.amount).label("total")
        ).where(and_(
            Expense.tenant_id == tenant_id,
            Expense.date >= start_date
        )).group_by("day").order_by("day")
        
        daily_result = await self.db.execute(daily_query)
        daily_stats = [{"date": str(row.day), "amount": float(row.total)} for row in daily_result.all()]

        # 3. Serie temporal semanal
        weekly_query = select(
            func.date_trunc('week', Expense.date).label("week"),
            func.sum(Expense.amount).label("total")
        ).where(and_(
            Expense.tenant_id == tenant_id,
            Expense.date >= start_date
        )).group_by("week").order_by("week")
        
        weekly_result = await self.db.execute(weekly_query)
        weekly_stats = [{"date": row.week.strftime("%Y-W%W"), "amount": float(row.total)} for row in weekly_result.all()]

        # 4. Serie temporal mensual
        monthly_query = select(
            func.date_trunc('month', Expense.date).label("month"),
            func.sum(Expense.amount).label("total")
        ).where(and_(
            Expense.tenant_id == tenant_id,
            Expense.date >= (start_date - timedelta(days=365))
        )).group_by("month").order_by("month")
        
        monthly_result = await self.db.execute(monthly_query)
        monthly_stats = [{"date": row.month.strftime("%Y-%m"), "amount": float(row.total)} for row in monthly_result.all()]
        
        return {
            "category_totals": category_totals,
            "total_amount": sum(category_totals.values()),
            "daily_stats": daily_stats,
            "weekly_stats": weekly_stats,
            "monthly_stats": monthly_stats
        }
