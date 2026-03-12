from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from ..models.stock_transfer import StockTransfer, StockTransferItem, StockTransferStatus
from ..models.product import Product
from ..models.product_branch import ProductBranch
from ..models.inventory_movement import InventoryMovement, MovementType
from ..schemas.stock_transfer import StockTransferCreate
from typing import List, Optional
from datetime import datetime

class StockTransferRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, tenant_id: int, skip: int = 0, limit: int = 100) -> List[StockTransfer]:
        query = select(StockTransfer).where(StockTransfer.tenant_id == tenant_id)\
            .options(
                selectinload(StockTransfer.from_branch),
                selectinload(StockTransfer.to_branch),
                selectinload(StockTransfer.user),
                selectinload(StockTransfer.items).selectinload(StockTransferItem.product)
            )\
            .order_by(StockTransfer.created_at.desc())\
            .offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, transfer_id: int, tenant_id: int) -> Optional[StockTransfer]:
        query = select(StockTransfer).where(
            and_(StockTransfer.id == transfer_id, StockTransfer.tenant_id == tenant_id)
        ).options(
            selectinload(StockTransfer.from_branch),
            selectinload(StockTransfer.to_branch),
            selectinload(StockTransfer.user),
            selectinload(StockTransfer.items).selectinload(StockTransferItem.product)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, obj_in: StockTransferCreate, user_id: int, tenant_id: int) -> StockTransfer:
        transfer = StockTransfer(
            tenant_id=tenant_id,
            from_branch_id=obj_in.from_branch_id,
            to_branch_id=obj_in.to_branch_id,
            user_id=user_id,
            notes=obj_in.notes,
            reference=obj_in.reference,
            status=obj_in.status or StockTransferStatus.PENDING
        )
        self.db.add(transfer)
        await self.db.flush()

        for item_in in obj_in.items:
            item = StockTransferItem(
                transfer_id=transfer.id,
                product_id=item_in.product_id,
                batch_id=item_in.batch_id,
                quantity=item_in.quantity
            )
            self.db.add(item)
        
        await self.db.flush()
        
        if transfer.status == StockTransferStatus.COMPLETED:
            await self._process_stock_update(transfer)
            
        return transfer

    async def complete_transfer(self, transfer: StockTransfer) -> StockTransfer:
        if transfer.status != StockTransferStatus.PENDING:
            raise ValueError("Solo se pueden completar traslados en estado pendiente")
        
        transfer.status = StockTransferStatus.COMPLETED
        transfer.completed_at = datetime.utcnow()
        await self._process_stock_update(transfer)
        return transfer

    async def cancel_transfer(self, transfer: StockTransfer) -> StockTransfer:
        if transfer.status != StockTransferStatus.PENDING:
            raise ValueError("Solo se pueden cancelar traslados en estado pendiente")
        
        transfer.status = StockTransferStatus.CANCELLED
        transfer.cancelled_at = datetime.utcnow()
        return transfer

    async def _process_stock_update(self, transfer: StockTransfer):
        """Lógica interna para mover el stock entre sucursales y registrar movimientos"""
        for item in transfer.items:
            # 1. Descontar de sucursal origen
            source_pb = await self._get_or_create_product_branch(item.product_id, transfer.from_branch_id)
            if source_pb.stock < item.quantity:
                # Opcional: Podríamos permitir stock negativo si la config lo dice, 
                # pero por ahora arrojamos error para mayor seguridad
                raise ValueError(f"Stock insuficiente en sucursal origen para el producto {item.product_id}")
            
            stock_before_source = source_pb.stock
            source_pb.stock -= item.quantity
            
            # 2. Aumentar en sucursal destino
            dest_pb = await self._get_or_create_product_branch(item.product_id, transfer.to_branch_id)
            stock_before_dest = dest_pb.stock
            dest_pb.stock += item.quantity
            
            # 3. Registrar Movimientos (Kardex)
            # Salida de Origen
            self.db.add(InventoryMovement(
                tenant_id=transfer.tenant_id,
                product_id=item.product_id,
                user_id=transfer.user_id,
                branch_id=transfer.from_branch_id,
                batch_id=item.batch_id,
                movement_type=MovementType.TRANSFER,
                quantity=-item.quantity,
                stock_before=stock_before_source,
                stock_after=source_pb.stock,
                reference=f"TR-{transfer.id}",
                notes=f"Salida por traslado a sucursal {transfer.to_branch_id}"
            ))
            
            # Entrada a Destino
            self.db.add(InventoryMovement(
                tenant_id=transfer.tenant_id,
                product_id=item.product_id,
                user_id=transfer.user_id,
                branch_id=transfer.to_branch_id,
                batch_id=item.batch_id,
                movement_type=MovementType.TRANSFER,
                quantity=item.quantity,
                stock_before=stock_before_dest,
                stock_after=dest_pb.stock,
                reference=f"TR-{transfer.id}",
                notes=f"Entrada por traslado desde sucursal {transfer.from_branch_id}"
            ))

    async def _get_or_create_product_branch(self, product_id: int, branch_id: int) -> ProductBranch:
        query = select(ProductBranch).where(
            and_(ProductBranch.product_id == product_id, ProductBranch.branch_id == branch_id)
        ).with_for_update()
        result = await self.db.execute(query)
        pb = result.scalar_one_or_none()
        
        if not pb:
            pb = ProductBranch(product_id=product_id, branch_id=branch_id, stock=0)
            self.db.add(pb)
            await self.db.flush()
            
        return pb
    async def get_stats(self, tenant_id: int) -> dict:
        """Calcula estadísticas generales de traslados para el tenant"""
        from sqlalchemy import func
        query = select(
            func.count(StockTransfer.id).label("total_count"),
            func.count(StockTransfer.id).filter(StockTransfer.status == StockTransferStatus.PENDING).label("pending_count"),
            func.count(StockTransfer.id).filter(StockTransfer.status == StockTransferStatus.COMPLETED).label("completed_count"),
            func.count(StockTransfer.id).filter(StockTransfer.status == StockTransferStatus.CANCELLED).label("cancelled_count")
        ).where(StockTransfer.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        row = result.fetchone()
        
        return {
            "total_count": row.total_count or 0,
            "pending_count": row.pending_count or 0,
            "completed_count": row.completed_count or 0,
            "cancelled_count": row.cancelled_count or 0
        }
