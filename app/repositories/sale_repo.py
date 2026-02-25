from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload, selectinload
from .base_repository import BaseRepository
from ..models.sale import Sale, SaleItem
from ..models.product import Product
from ..models.inventory_movement import InventoryMovement, MovementType
from ..core.exceptions import ProductNotFoundException, InsufficientStockException
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

class SaleRepository(BaseRepository[Sale]):
    def __init__(self, db: AsyncSession):
        super().__init__(Sale, db)

    async def get_by_id(self, id: int, tenant_id: Optional[int] = None) -> Optional[Sale]:
        """Obtiene una venta con sus items y productos cargados"""
        query = select(Sale).options(
            joinedload(Sale.items).joinedload(SaleItem.product)
        ).where(Sale.id == id)
        
        if tenant_id is not None:
            query = query.where(Sale.tenant_id == tenant_id)
            
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def create_sale(self, tenant_id: int, user_id: int, sale_data) -> Sale:
        """
        Crea una venta, actualiza el stock y registra los movimientos de inventario.
        Todo se ejecuta dentro de la misma transacción.
        """
        total_amount = Decimal(0)
        sale_items = []
        
        # 1. Crear la venta (sin items todavía para tener el ID)
        new_sale = Sale(
            tenant_id=tenant_id,
            user_id=user_id,
            payment_method=sale_data.payment_method,
            notes=sale_data.notes,
            total_amount=0
        )
        self.db.add(new_sale)
        await self.db.flush() # Para obtener el ID

        for item_data in sale_data.items:
            # 2. Verificar producto y stock
            result = await self.db.execute(
                select(Product).where(Product.id == item_data.product_id, Product.tenant_id == tenant_id)
            )
            product = result.scalar_one_or_none()
            
            if not product:
                raise ProductNotFoundException(item_data.product_id)
            
            if product.stock < item_data.quantity:
                raise InsufficientStockException(product.name, item_data.quantity, product.stock)
            
            # 3. Calcular subtotal
            subtotal = Decimal(str(item_data.quantity)) * Decimal(str(item_data.unit_price))
            total_amount += subtotal
            
            # 4. Crear SaleItem
            sale_item = SaleItem(
                sale_id=new_sale.id,
                product_id=product.id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                subtotal=subtotal
            )
            sale_items.append(sale_item)
            
            # 5. Actualizar stock del producto
            stock_before = product.stock
            product.stock -= item_data.quantity
            
            # 6. Registrar movimiento de inventario
            movement = InventoryMovement(
                tenant_id=tenant_id,
                product_id=product.id,
                user_id=user_id,
                movement_type=MovementType.EXIT,
                quantity=-item_data.quantity,
                stock_before=stock_before,
                stock_after=product.stock,
                unit_cost=product.cost,
                reference=f"VENTA #{new_sale.id}",
                notes=f"Venta realizada por el POS"
            )
            self.db.add(movement)

        # 7. Actualizar total de la venta
        new_sale.total_amount = total_amount
        self.db.add_all(sale_items)
        
        await self.db.commit()
        
        # Retornar la venta con todas sus relaciones cargadas usando el nuevo get_by_id
        return await self.get_by_id(new_sale.id, tenant_id)

    async def annul_sale(self, sale_id: int, tenant_id: int, user_id: int) -> Sale:
        """Enula una venta, revierte el stock y registra los ajustes"""
        sale = await self.get_by_id(sale_id, tenant_id)
        if not sale:
            return None
        
        if sale.status == "annulled":
            raise Exception("La venta ya ha sido anulada")

        # 1. Revertir Stock de cada ítem
        for item in sale.items:
            product = item.product
            stock_before = product.stock
            product.stock += item.quantity
            
            # Registrar movimiento de ajuste (Entrada por anulación)
            adjustment = InventoryMovement(
                tenant_id=tenant_id,
                product_id=product.id,
                user_id=user_id,
                movement_type=MovementType.ADJUSTMENT,
                quantity=item.quantity,
                stock_before=stock_before,
                stock_after=product.stock,
                unit_cost=product.cost,
                reference=f"ANULACIÓN #{sale.id}",
                notes=f"Anulación de venta realizada"
            )
            self.db.add(adjustment)

        # 2. Marcar venta como anulada
        sale.status = "annulled"
        
        await self.db.commit()
        await self.db.refresh(sale)
        return sale

    async def get_sales_paginated(
        self, 
        tenant_id: int, 
        page: int = 1, 
        size: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        payment_method: Optional[str] = None,
        search: Optional[str] = None,
        seller_id: Optional[int] = None
    ):
        offset = (page - 1) * size
        
        query = select(Sale).options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.user)
        ).where(Sale.tenant_id == tenant_id)

        # Aplicar filtros
        if seller_id:
            query = query.where(Sale.user_id == seller_id)

        if search:
            # Buscar por ID si es número, o por nombre de producto en los items
            if search.isdigit():
                query = query.where(Sale.id == int(search))
            else:
                # Búsqueda por producto
                product_search = select(SaleItem.sale_id).join(Product).where(
                    and_(
                        SaleItem.product_id == Product.id,
                        Product.name.ilike(f"%{search}%")
                    )
                )
                query = query.where(Sale.id.in_(product_search))

        if start_date:
            query = query.where(Sale.created_at >= start_date)
        if end_date:
            query = query.where(Sale.created_at <= end_date)
        if status:
            query = query.where(Sale.status == status)
        if payment_method:
            query = query.where(Sale.payment_method == payment_method)

        query = query.order_by(Sale.created_at.desc())
        
        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        # Obtener items
        result = await self.db.execute(query.offset(offset).limit(size))
        items = result.unique().scalars().all()
        
        return items, total
