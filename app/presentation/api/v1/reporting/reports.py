"""Analítica: dashboard, rentabilidad y KPIs del historial de ventas."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.reporting.dashboard import build_dashboard
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User, UserRole
from app.infrastructure.persistence.repositories.reporting.report_repo import ReportRepository
from app.presentation.dependencies import require_permission, require_role
from app.presentation.schemas.reporting.report import InventoryReport

router = APIRouter()

ADMIN_OR_MANAGER = [UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPERADMIN]


@router.get("/dashboard", response_model=InventoryReport)
async def get_dashboard_data(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_role(ADMIN_OR_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Datos del dashboard inicial (Solo Admins/Managers)"""
    return await build_dashboard(ReportRepository(db), current_user.tenant_id, start_date, end_date)


@router.get("/profitability")
async def get_profitability_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_role(ADMIN_OR_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Reporte de rentabilidad por producto"""
    return await ReportRepository(db).get_profitability_report(current_user.tenant_id, start_date, end_date)


@router.get("/sales-history-stats")
async def get_sales_history_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    seller_id: Optional[int] = Query(None),
    current_user: User = Depends(require_permission("sales:view")),
    db: AsyncSession = Depends(get_db),
):
    """KPIs y tendencias para la página de historial de ventas"""
    return await ReportRepository(db).get_sales_history_stats(
        tenant_id=current_user.tenant_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        payment_method=payment_method,
        search=search,
        seller_id=seller_id,
    )
