from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from .base_service import BaseService
from ..repositories.inventory_audit_repo import InventoryAuditRepository
from ..repositories.product_repo import ProductRepository
from ..models.inventory_audit import InventoryAudit, InventoryAuditItem, AuditStatus
from ..services.inventory_service import InventoryService
from ..core.exceptions import (
    ProductNotFoundException,
    InvalidStockOperationException
)
from datetime import datetime

class InventoryAuditService(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.audit_repo = InventoryAuditRepository(db)
        self.product_repo = ProductRepository(db)
        self.inventory_service = InventoryService(db)

    async def start_audit(self, branch_id: int, tenant_id: int, user_id: int, notes: Optional[str] = None) -> InventoryAudit:
        """Inicia una nueva sesión de auditoría"""
        audit_data = {
            "tenant_id": tenant_id,
            "branch_id": branch_id,
            "user_id": user_id,
            "notes": notes,
            "status": AuditStatus.IN_PROGRESS,
            "started_at": datetime.utcnow()
        }
        audit = await self.audit_repo.create(audit_data)
        await self.commit()
        # Retornar con relaciones cargadas para evitar MissingGreenlet en serialización
        return await self.audit_repo.get_with_items(audit.id, tenant_id)

    async def add_counted_item(self, audit_id: int, product_id: int, counted_stock: int, tenant_id: int, notes: Optional[str] = None) -> InventoryAuditItem:
        """Registra el conteo de un producto en la auditoría"""
        audit = await self.audit_repo.get_with_items(audit_id, tenant_id)
        if not audit or audit.status != AuditStatus.IN_PROGRESS:
            raise InvalidStockOperationException("Auditoría no encontrada o ya finalizada")

        # Obtener stock esperado actual en esa sucursal
        from sqlalchemy import select
        from ..models.product_branch import ProductBranch
        query = select(ProductBranch).where(
            ProductBranch.product_id == product_id,
            ProductBranch.branch_id == audit.branch_id
        )
        result = await self.db.execute(query)
        pb = result.scalar_one_or_none()
        expected_stock = pb.stock if pb else 0

        # Crear o actualizar item de auditoría
        existing_item = next((item for item in audit.items if item.product_id == product_id), None)
        
        if existing_item:
            existing_item.counted_stock = counted_stock
            existing_item.difference = counted_stock - expected_stock
            existing_item.notes = notes
            item = existing_item
        else:
            item_data = {
                "audit_id": audit_id,
                "product_id": product_id,
                "expected_stock": expected_stock,
                "counted_stock": counted_stock,
                "difference": counted_stock - expected_stock,
                "notes": notes
            }
            item = await self.audit_repo.create_item(item_data)

        # Cargar la relación product para evitar MissingGreenlet en serialización
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        query = select(InventoryAuditItem).options(
            selectinload(InventoryAuditItem.product)
        ).where(InventoryAuditItem.id == item.id)
        result = await self.db.execute(query)
        item = result.scalar_one()

        await self.commit()
        return item

    async def complete_audit(self, audit_id: int, tenant_id: int) -> InventoryAudit:
        """Finaliza la auditoría y aplica los ajustes de stock"""
        audit = await self.audit_repo.get_with_items(audit_id, tenant_id)
        if not audit or audit.status != AuditStatus.IN_PROGRESS:
            raise InvalidStockOperationException("Auditoría no encontrada o ya finalizada")

        # Aplicar ajustes por cada item contado
        for item in audit.items:
            if not item.is_adjusted and item.difference != 0:
                # Usar adjust_stock del inventario
                await self.inventory_service.adjust_stock(
                    product_id=item.product_id,
                    branch_id=audit.branch_id,
                    new_stock=item.counted_stock,
                    tenant_id=tenant_id,
                    reason=f"Ajuste por Auditoría #{audit.id}"
                )
                item.is_adjusted = True

        audit.status = AuditStatus.COMPLETED
        audit.completed_at = datetime.utcnow()
        await self.commit()
        return audit
