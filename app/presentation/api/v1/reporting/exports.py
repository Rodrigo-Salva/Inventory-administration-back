"""Exportaciones (Excel, CSV, PDF). Cada endpoint consulta y delega el formato a los generadores."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.shared.pagination import PaginationParams
from app.infrastructure.external.excel_report import build_csv, build_excel
from app.infrastructure.external.report_generator import ReportGenerator
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User, UserRole
from app.infrastructure.persistence.repositories.catalog.category_repo import CategoryRepository
from app.infrastructure.persistence.repositories.catalog.product_repo import ProductRepository
from app.infrastructure.persistence.repositories.catalog.supplier_repo import SupplierRepository
from app.infrastructure.persistence.repositories.identity.tenant_repo import TenantRepository
from app.infrastructure.persistence.repositories.identity.user_repo import UserRepository
from app.infrastructure.persistence.repositories.inventory.adjustment_repo import AdjustmentRepository
from app.infrastructure.persistence.repositories.inventory.inventory_movement_repo import (
    InventoryMovementRepository,
)
from app.infrastructure.persistence.repositories.purchasing.expense_repo import ExpenseRepository
from app.infrastructure.persistence.repositories.purchasing.purchase_repo import PurchaseRepository
from app.infrastructure.persistence.repositories.reporting.report_repo import ReportRepository
from app.infrastructure.persistence.repositories.sales.customer_repo import CustomerRepository
from app.infrastructure.persistence.repositories.sales.sale_repo import SaleRepository
from app.presentation.api.v1.reporting.responses import csv_response, excel_response, pdf_response
from app.presentation.dependencies import require_permission, require_role

router = APIRouter()

ADMIN_OR_MANAGER = [UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPERADMIN]
STATUS_LABEL = {True: "ACTIVO", False: "INACTIVO"}


async def _tenant_name(db: AsyncSession, tenant_id: int) -> str | None:
    tenant = await TenantRepository(db).get_by_id(tenant_id)
    return tenant.name if tenant else None


def _fmt(value: datetime, pattern: str = "%d/%m/%Y %H:%M") -> str:
    return value.strftime(pattern)


def _items_summary(items) -> str:
    return ", ".join(f"{i.product.name} (x{i.quantity})" for i in items if i.product)


@router.get("/inventory-csv")
async def export_inventory_csv(
    category_id: Optional[int] = Query(None),
    supplier_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_permission("products:download")),
    db: AsyncSession = Depends(get_db),
):
    """CSV del inventario actual con filtros opcionales"""
    products, _ = await ProductRepository(db).get_filtered(
        tenant_id=current_user.tenant_id, category_id=category_id, supplier_id=supplier_id, is_active=is_active
    )
    content = build_csv(
        ["ID", "SKU", "Nombre", "Categoría", "Stock", "Precio", "Costo", "Estado"],
        (
            [p.id, p.sku, p.name, p.category.name if p.category else "", p.stock, p.price, p.cost,
             "Activo" if p.is_active else "Inactivo"]
            for p in products
        ),
    )
    return csv_response(content, "inventario", stamp=datetime.now().strftime("%Y%m%d_%H%M%S"))


@router.get("/inventory-excel")
async def export_inventory_excel(
    category_id: Optional[int] = Query(None),
    supplier_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_role(ADMIN_OR_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Excel profesional del inventario (Solo Admins/Managers)"""
    tenant_id = current_user.tenant_id
    products, _ = await ProductRepository(db).get_filtered(
        tenant_id=tenant_id, category_id=category_id, supplier_id=supplier_id,
        is_active=is_active, start_date=start_date, end_date=end_date,
    )
    buffer = build_excel(
        sheet="Inventario", title="REPORTE DE PRODUCTOS", tenant_name=await _tenant_name(db, tenant_id),
        headers=["ID", "SKU", "Nombre", "Categoría", "Stock", "Mínimo", "Precio", "Costo", "Estado"],
        rows=(
            [p.id, p.sku, p.name, p.category.name if p.category else "Sin categoría", p.stock,
             p.min_stock, float(p.price), float(p.cost or 0), STATUS_LABEL[bool(p.is_active)]]
            for p in products
        ),
        width=15, money_columns=(7, 8), show_range=True, start=start_date, end=end_date,
    )
    return excel_response(buffer, "Productos")


@router.get("/suppliers-excel")
async def export_suppliers_excel(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_permission("suppliers:view")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    suppliers, _ = await SupplierRepository(db).get_filtered(
        tenant_id=tenant_id, search=search, is_active=is_active, start_date=start_date, end_date=end_date
    )
    buffer = build_excel(
        sheet="Proveedores", title="REPORTE DE PROVEEDORES", tenant_name=await _tenant_name(db, tenant_id),
        headers=["ID", "Código", "Nombre", "Email", "Teléfono", "RUC", "Estado", "Fecha Registro"],
        rows=(
            [s.id, s.code, s.name, s.email, s.phone, s.tax_id, STATUS_LABEL[bool(s.is_active)], _fmt(s.created_at)]
            for s in suppliers
        ),
        width=18, show_range=True, start=start_date, end=end_date,
    )
    return excel_response(buffer, "Proveedores")


@router.get("/categories-excel")
async def export_categories_excel(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_permission("categories:view")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    categories, _ = await CategoryRepository(db).get_filtered(
        tenant_id=tenant_id, search=search, is_active=is_active, start_date=start_date, end_date=end_date
    )
    buffer = build_excel(
        sheet="Categorías", title="REPORTE DE CATEGORÍAS", tenant_name=await _tenant_name(db, tenant_id),
        headers=["ID", "Código", "Nombre", "Descripción", "Estado", "Fecha Registro"],
        rows=(
            [c.id, c.code, c.name, c.description, STATUS_LABEL[bool(c.is_active)], _fmt(c.created_at)]
            for c in categories
        ),
        width=18, show_range=True, start=start_date, end=end_date,
    )
    return excel_response(buffer, "Categorias")


@router.get("/users-excel")
async def export_users_excel(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_permission("users:view")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    users, _ = await UserRepository(db).get_filtered(
        tenant_id=tenant_id, search=search, is_active=is_active, start_date=start_date, end_date=end_date
    )
    buffer = build_excel(
        sheet="Usuarios", title="REPORTE DE USUARIOS", tenant_name=await _tenant_name(db, tenant_id),
        headers=["ID", "Email", "Tipo", "Estado", "Fecha Registro"],
        rows=(
            [u.id, u.email, "ADMIN" if u.is_admin else "OPERADOR", STATUS_LABEL[bool(u.is_active)], _fmt(u.created_at)]
            for u in users
        ),
        show_range=True, start=start_date, end=end_date,
    )
    return excel_response(buffer, "Usuarios")


@router.get("/movements-excel")
async def export_movements_excel(
    product_id: Optional[int] = Query(None),
    movement_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_permission("inventory:view")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    movements, _ = await InventoryMovementRepository(db).get_filtered(
        tenant_id=tenant_id, product_id=product_id, movement_type=movement_type,
        start_date=start_date, end_date=end_date,
    )
    buffer = build_excel(
        sheet="Movimientos", title="KARDEX DE MOVIMIENTOS", tenant_name=await _tenant_name(db, tenant_id),
        headers=["ID", "Fecha", "Producto", "Tipo", "Cantidad", "Stock Anterior", "Stock Nuevo", "Referencia", "Notas"],
        rows=(
            [m.id, _fmt(m.created_at), m.product.name if m.product else "N/A", m.movement_type.upper(),
             m.quantity, m.stock_before, m.stock_after, m.reference, m.notes]
            for m in movements
        ),
        width=18, show_range=True, start=start_date, end=end_date,
    )
    return excel_response(buffer, "Kardex")


@router.get("/sales-excel")
async def export_sales_excel(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("sales:view")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    sales = await ReportRepository(db).get_filtered_sales(
        tenant_id=tenant_id, start_date=start_date, end_date=end_date,
        status=status, payment_method=payment_method,
    )
    buffer = build_excel(
        sheet="Ventas", title="REPORTE DE VENTAS", tenant_name=await _tenant_name(db, tenant_id),
        headers=["ID", "Fecha/Hora", "Método", "Vendedor", "Estado", "Items", "Total"],
        rows=(
            [s.id, _fmt(s.created_at), s.payment_method.upper(), s.user.email.split("@")[0] if s.user else "N/A",
             s.status.upper(), _items_summary(s.items), float(s.total_amount)]
            for s in sales
        ),
        column_widths={"F": 50}, money_columns=(7,), show_range=True, start=start_date, end=end_date,
        empty_range_label="Historial Completo",
    )
    return excel_response(buffer, "Ventas")


@router.get("/sales-pdf")
async def export_sales_pdf(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("sales:view")),
    db: AsyncSession = Depends(get_db),
):
    """PDF resumen de ventas (hasta 500 ventas)"""
    tenant_id = current_user.tenant_id
    sales, _ = await SaleRepository(db).get_sales_paginated(
        tenant_id=tenant_id, pagination=PaginationParams(page=1, page_size=500),
        start_date=start_date, end_date=end_date, status=status, payment_method=payment_method, search=search,
    )
    filters = {"start_date": start_date, "end_date": end_date, "status": status,
               "payment_method": payment_method, "search": search}
    tenant_name = await _tenant_name(db, tenant_id) or "Inventory Administration"
    return pdf_response(ReportGenerator.generate_sales_summary_pdf(sales, tenant_name, filters), "Reporte_Ventas")


async def _expenses(db: AsyncSession, user: User, category, start_date, end_date, search):
    expenses, _ = await ExpenseRepository(db).get_by_tenant(
        tenant_id=user.tenant_id, limit=1000, category=category,
        start_date=start_date, end_date=end_date, search=search,
    )
    return expenses


@router.get("/expenses-csv")
async def export_expenses_csv(
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("expenses:export")),
    db: AsyncSession = Depends(get_db),
):
    expenses = await _expenses(db, current_user, category, start_date, end_date, search)
    content = build_csv(
        ["Fecha", "Categoría", "Descripción", "Referencia", "Monto"],
        ([e.date, e.category, e.description, e.reference or "", e.amount] for e in expenses),
    )
    return csv_response(content, "Gastos")


@router.get("/expenses-excel")
async def export_expenses_excel(
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("expenses:export")),
    db: AsyncSession = Depends(get_db),
):
    expenses = await _expenses(db, current_user, category, start_date, end_date, search)
    buffer = build_excel(
        sheet="Gastos", title="REPORTE DE GASTOS",
        tenant_name=await _tenant_name(db, current_user.tenant_id),
        headers=["FECHA", "CATEGORÍA", "DESCRIPCIÓN", "REFERENCIA", "MONTO"],
        rows=([e.date, e.category, e.description, e.reference or "", float(e.amount)] for e in expenses),
        column_widths={"C": 40}, money_columns=(5,),
    )
    return excel_response(buffer, "Gastos")


@router.get("/expenses-pdf")
async def export_expenses_pdf(
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("expenses:export")),
    db: AsyncSession = Depends(get_db),
):
    expenses = await _expenses(db, current_user, category, start_date, end_date, search)
    filters = {"category": category, "start_date": start_date, "end_date": end_date, "search": search}
    tenant_name = await _tenant_name(db, current_user.tenant_id) or "Inventory Administration"
    return pdf_response(ReportGenerator.generate_expenses_pdf(expenses, tenant_name, filters), "Reporte_Gastos")


@router.get("/customers-excel")
async def export_customers_excel(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_permission("customers:view")),
    db: AsyncSession = Depends(get_db),
):
    customers, _ = await CustomerRepository(db).get_filtered(
        tenant_id=current_user.tenant_id, search=search, is_active=is_active,
        start_date=start_date, end_date=end_date,
    )
    buffer = build_excel(
        sheet="Clientes", title="REPORTE DE CLIENTES",
        tenant_name=await _tenant_name(db, current_user.tenant_id),
        headers=["ID", "NOMBRE", "DOCUMENTO", "EMAIL", "TELÉFONO", "ESTADO"],
        rows=(
            [c.id, c.name, c.document_number or "", c.email or "", c.phone or "", STATUS_LABEL[bool(c.is_active)]]
            for c in customers
        ),
        column_widths={"B": 35},
    )
    return excel_response(buffer, "Clientes")


@router.get("/purchases-excel")
async def export_purchases_excel(
    status: Optional[str] = Query(None),
    supplier_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_permission("purchases:view")),
    db: AsyncSession = Depends(get_db),
):
    purchases, _ = await PurchaseRepository(db).get_filtered(
        tenant_id=current_user.tenant_id, status=status, supplier_id=supplier_id, search=search,
        start_date=start_date, end_date=end_date, pagination=PaginationParams(page=1, page_size=1000),
    )
    buffer = build_excel(
        sheet="Compras", title="REPORTE DE COMPRAS",
        tenant_name=await _tenant_name(db, current_user.tenant_id),
        headers=["ID", "FECHA", "PROVEEDOR", "REFERENCIA", "ESTADO", "ITEMS", "TOTAL"],
        rows=(
            [p.id, _fmt(p.created_at, "%d/%m/%Y"), p.supplier.name if p.supplier else "N/A",
             p.reference_number or "", p.status.value, _items_summary(p.items), float(p.total_amount)]
            for p in purchases
        ),
        column_widths={"F": 40}, money_columns=(7,),
    )
    return excel_response(buffer, "Compras")


@router.get("/adjustments-excel")
async def export_adjustments_excel(
    product_id: Optional[int] = Query(None),
    adjustment_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_permission("inventory:adjust")),
    db: AsyncSession = Depends(get_db),
):
    adjustments = await AdjustmentRepository(db).get_filtered(
        tenant_id=current_user.tenant_id, product_id=product_id, adjustment_type=adjustment_type,
        start_date=start_date, end_date=end_date, limit=1000,
    )
    buffer = build_excel(
        sheet="Ajustes", title="REPORTE DE AJUSTES",
        tenant_name=await _tenant_name(db, current_user.tenant_id),
        headers=["ID", "FECHA", "PRODUCTO", "TIPO", "CANTIDAD", "RAZÓN", "NOTAS"],
        rows=(
            [a.id, _fmt(a.created_at), a.product.name if a.product else "N/A", a.adjustment_type,
             a.quantity, a.reason.value, a.notes or ""]
            for a in adjustments
        ),
        column_widths={"C": 35},
    )
    return excel_response(buffer, "Ajustes")
