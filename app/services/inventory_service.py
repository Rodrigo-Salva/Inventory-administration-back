from typing import Optional, Dict, Any, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from .base_service import BaseService
from ..repositories import ProductRepository, InventoryMovementRepository
from ..models import Product, InventoryMovement, MovementType, AlertType, AlertStatus
from ..core.exceptions import (
    ProductNotFoundException,
    InsufficientStockException,
    InvalidStockOperationException
)
from ..core.logging_config import get_logger
from .notification_service import NotificationService
from .stock_alert_service import StockAlertService
from fastapi import BackgroundTasks

logger = get_logger(__name__)


class InventoryService(BaseService):
    """Servicio para gestión de inventario"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.product_repo = ProductRepository(db)
        self.movement_repo = InventoryMovementRepository(db)
        self.alert_service = StockAlertService(db)
    
    async def add_stock(
        self,
        product_id: int,
        branch_id: int,
        quantity: int,
        tenant_id: int,
        user_id: Optional[int] = None,
        unit_cost: Optional[Decimal] = None,
        reference: Optional[str] = None,
        notes: Optional[str] = None,
        aisle: Optional[str] = None,
        shelf: Optional[str] = None,
        bin: Optional[str] = None
    ) -> InventoryMovement:
        """
        Agrega stock a un producto
        
        Args:
            product_id: ID del producto
            quantity: Cantidad a agregar (debe ser positivo)
            tenant_id: ID del tenant
            user_id: ID del usuario que realiza la operación
            unit_cost: Costo unitario del producto
            reference: Referencia externa (factura, orden de compra, etc.)
            notes: Notas adicionales
            aisle: Pasillo
            shelf: Estante
            bin: Gaveta
        
        Returns:
            InventoryMovement creado
        
        Raises:
            ProductNotFoundException: Si el producto no existe
            InvalidStockOperationException: Si la cantidad es inválida
        """
        if quantity <= 0:
            raise InvalidStockOperationException("La cantidad debe ser mayor a 0")
        
        # Obtener producto
        product = await self.product_repo.get_by_id(product_id, tenant_id)
        if not product:
            raise ProductNotFoundException(product_id)
        
        # Obtener stock de la sucursal
        from sqlalchemy import select
        from ..models.product_branch import ProductBranch
        query = select(ProductBranch).where(
            ProductBranch.product_id == product_id,
            ProductBranch.branch_id == branch_id
        )
        result = await self.db.execute(query)
        product_branch = result.scalar_one_or_none()

        if not product_branch:
            # Crear la asignación a la sucursal automáticamente
            product_branch = ProductBranch(
                product_id=product_id,
                branch_id=branch_id,
                stock=0,
                min_stock=product.min_stock,
                max_stock=product.max_stock,
                aisle=aisle,
                shelf=shelf,
                bin=bin
            )
            self.db.add(product_branch)
        else:
            # Actualizar ubicación si se proporciona
            if aisle is not None: product_branch.aisle = aisle
            if shelf is not None: product_branch.shelf = shelf
            if bin is not None: product_branch.bin = bin
            
        # Guardar stock anterior
        stock_before = product_branch.stock
        
        # Actualizar stock
        product_branch.stock += quantity
        stock_after = product_branch.stock
        
        # Sincronizar stock total en el producto padre
        product.stock += quantity
        
        # Crear movimiento
        movement_data = {
            "tenant_id": tenant_id,
            "product_id": product_id,
            "branch_id": branch_id,
            "user_id": user_id,
            "movement_type": MovementType.ENTRY,
            "quantity": quantity,
            "stock_before": stock_before,
            "stock_after": stock_after,
            "unit_cost": unit_cost,
            "reference": reference,
            "notes": notes
        }
        
        movement = await self.movement_repo.create(movement_data)
        
        # Verificar y resolver alertas de stock bajo si aplica
        await self.alert_service.resolve_alerts_if_needed(product, tenant_id)
        
        await self.commit()
        
        logger.info(f"Stock agregado: Producto {product_id}, Cantidad {quantity}, Nuevo stock: {stock_after}")
        
        return movement
    
    async def remove_stock(
        self,
        product_id: int,
        branch_id: int,
        quantity: int,
        tenant_id: int,
        user_id: Optional[int] = None,
        reference: Optional[str] = None,
        notes: Optional[str] = None,
        aisle: Optional[str] = None,
        shelf: Optional[str] = None,
        bin: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> InventoryMovement:
        """
        Remueve stock de un producto
        
        Args:
            product_id: ID del producto
            quantity: Cantidad a remover (debe ser positivo)
            tenant_id: ID del tenant
            user_id: ID del usuario que realiza la operación
            reference: Referencia externa
            notes: Notas adicionales
            aisle: Pasillo
            shelf: Estante
            bin: Gaveta
        
        Returns:
            InventoryMovement creado
        
        Raises:
            ProductNotFoundException: Si el producto no existe
            InsufficientStockException: Si no hay suficiente stock
            InvalidStockOperationException: Si la cantidad es inválida
        """
        if quantity <= 0:
            raise InvalidStockOperationException("La cantidad debe ser mayor a 0")
        
        # Obtener producto
        product = await self.product_repo.get_by_id(product_id, tenant_id)
        if not product:
            raise ProductNotFoundException(product_id)
        
        # Verificar stock en la sucursal
        from sqlalchemy import select
        from ..models.product_branch import ProductBranch
        query = select(ProductBranch).where(
            ProductBranch.product_id == product_id,
            ProductBranch.branch_id == branch_id
        )
        result = await self.db.execute(query)
        product_branch = result.scalar_one_or_none()

        if not product_branch:
             # Crear la asignación a la sucursal automáticamente
            product_branch = ProductBranch(
                product_id=product_id,
                branch_id=branch_id,
                stock=0,
                min_stock=product.min_stock,
                max_stock=product.max_stock,
                aisle=aisle,
                shelf=shelf,
                bin=bin
            )
            self.db.add(product_branch)
        else:
            # Actualizar ubicación si se proporciona
            if aisle is not None: product_branch.aisle = aisle
            if shelf is not None: product_branch.shelf = shelf
            if bin is not None: product_branch.bin = bin
        
        if product_branch.stock < quantity:
            raise InsufficientStockException(product.name, quantity, product_branch.stock)
        
        # Guardar stock anterior
        stock_before = product_branch.stock
        
        # Actualizar stock
        product_branch.stock -= quantity
        stock_after = product_branch.stock
        
        # Sincronizar stock padre
        product.stock -= quantity
        
        # Crear movimiento (cantidad negativa para salidas)
        movement_data = {
            "tenant_id": tenant_id,
            "product_id": product_id,
            "branch_id": branch_id,
            "user_id": user_id,
            "movement_type": MovementType.EXIT,
            "quantity": -quantity,  # Negativo para salidas
            "stock_before": stock_before,
            "stock_after": stock_after,
            "reference": reference,
            "notes": notes
        }
        
        movement = await self.movement_repo.create(movement_data)
        
        # Verificar y crear alertas si es necesario
        await self._check_and_create_alerts(product, tenant_id, background_tasks)
        
        await self.commit()
        
        logger.info(f"Stock removido: Producto {product_id}, Cantidad {quantity}, Nuevo stock: {stock_after}")
        
        return movement
    
    async def adjust_stock(
        self,
        product_id: int,
        branch_id: int,
        new_stock: int,
        tenant_id: int,
        user_id: Optional[int] = None,
        reason: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> InventoryMovement:
        """
        Ajusta el stock de un producto a un valor específico
        
        Args:
            product_id: ID del producto
            new_stock: Nuevo valor de stock
            tenant_id: ID del tenant
            user_id: ID del usuario que realiza el ajuste
            reason: Razón del ajuste
        
        Returns:
            InventoryMovement creado
        """
        if new_stock < 0:
            raise InvalidStockOperationException("El stock no puede ser negativo")
        
        # Obtener producto
        product = await self.product_repo.get_by_id(product_id, tenant_id)
        if not product:
            raise ProductNotFoundException(product_id)
        
        # Obtener stock de la sucursal
        from sqlalchemy import select
        from ..models.product_branch import ProductBranch
        query = select(ProductBranch).where(
            ProductBranch.product_id == product_id,
            ProductBranch.branch_id == branch_id
        )
        result = await self.db.execute(query)
        product_branch = result.scalar_one_or_none()

        if not product_branch:
            # Crear la asignación a la sucursal automáticamente
            product_branch = ProductBranch(
                product_id=product_id,
                branch_id=branch_id,
                stock=0,
                min_stock=product.min_stock,
                max_stock=product.max_stock
            )
            self.db.add(product_branch)
            
        # Calcular diferencia
        stock_before = product_branch.stock
        difference = new_stock - stock_before
        
        if difference == 0:
            raise InvalidStockOperationException("El nuevo stock es igual al actual en esta sucursal")
        
        # Actualizar stock
        product_branch.stock = new_stock
        
        # Sincronizar stock padre
        product.stock += difference
        
        # Crear movimiento
        movement_data = {
            "tenant_id": tenant_id,
            "product_id": product_id,
            "branch_id": branch_id,
            "user_id": user_id,
            "movement_type": MovementType.ADJUSTMENT,
            "quantity": difference,
            "stock_before": stock_before,
            "stock_after": new_stock,
            "notes": f"Ajuste de inventario: {reason}" if reason else "Ajuste de inventario"
        }
        
        movement = await self.movement_repo.create(movement_data)
        
        # Verificar alertas
        if difference < 0:
            await self._check_and_create_alerts(product, tenant_id, background_tasks)
        else:
            await self._check_and_resolve_alerts(product, tenant_id)
        
        await self.commit()
        
        logger.info(f"Stock ajustado: Producto {product_id}, De {stock_before} a {new_stock}")
        
        return movement
    
    async def _check_and_create_alerts(self, product: Product, tenant_id: int, background_tasks: Optional[BackgroundTasks] = None):
        """Redirige al servicio centralizado"""
        await self.alert_service.check_and_trigger_alerts(product, tenant_id, background_tasks)
    
    async def _check_and_resolve_alerts(self, product: Product, tenant_id: int):
        """Redirige al servicio centralizado"""
        await self.alert_service.resolve_alerts_if_needed(product, tenant_id)
