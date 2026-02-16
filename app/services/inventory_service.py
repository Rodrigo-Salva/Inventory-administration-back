from typing import Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from .base_service import BaseService
from ..repositories import ProductRepository, InventoryMovementRepository, StockAlertRepository
from ..models import Product, InventoryMovement, MovementType, StockAlert, AlertType, AlertStatus
from ..core.exceptions import (
    ProductNotFoundException,
    InsufficientStockException,
    InvalidStockOperationException
)
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class InventoryService(BaseService):
    """Servicio para gestión de inventario"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.product_repo = ProductRepository(db)
        self.movement_repo = InventoryMovementRepository(db)
        self.alert_repo = StockAlertRepository(db)
    
    async def add_stock(
        self,
        product_id: int,
        quantity: int,
        tenant_id: int,
        user_id: Optional[int] = None,
        unit_cost: Optional[Decimal] = None,
        reference: Optional[str] = None,
        notes: Optional[str] = None
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
        
        # Guardar stock anterior
        stock_before = product.stock
        
        # Actualizar stock
        product.stock += quantity
        stock_after = product.stock
        
        # Crear movimiento
        movement_data = {
            "tenant_id": tenant_id,
            "product_id": product_id,
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
        await self._check_and_resolve_alerts(product, tenant_id)
        
        await self.commit()
        
        logger.info(f"Stock agregado: Producto {product_id}, Cantidad {quantity}, Nuevo stock: {stock_after}")
        
        return movement
    
    async def remove_stock(
        self,
        product_id: int,
        quantity: int,
        tenant_id: int,
        user_id: Optional[int] = None,
        reference: Optional[str] = None,
        notes: Optional[str] = None,
        allow_negative: bool = False
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
            allow_negative: Permitir stock negativo
        
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
        
        # Verificar stock suficiente
        if not allow_negative and product.stock < quantity:
            raise InsufficientStockException(product.name, quantity, product.stock)
        
        # Guardar stock anterior
        stock_before = product.stock
        
        # Actualizar stock
        product.stock -= quantity
        stock_after = product.stock
        
        # Crear movimiento (cantidad negativa para salidas)
        movement_data = {
            "tenant_id": tenant_id,
            "product_id": product_id,
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
        await self._check_and_create_alerts(product, tenant_id)
        
        await self.commit()
        
        logger.info(f"Stock removido: Producto {product_id}, Cantidad {quantity}, Nuevo stock: {stock_after}")
        
        return movement
    
    async def adjust_stock(
        self,
        product_id: int,
        new_stock: int,
        tenant_id: int,
        user_id: Optional[int] = None,
        reason: Optional[str] = None
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
        
        # Calcular diferencia
        stock_before = product.stock
        difference = new_stock - stock_before
        
        if difference == 0:
            raise InvalidStockOperationException("El nuevo stock es igual al actual")
        
        # Actualizar stock
        product.stock = new_stock
        
        # Crear movimiento
        movement_data = {
            "tenant_id": tenant_id,
            "product_id": product_id,
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
            await self._check_and_create_alerts(product, tenant_id)
        else:
            await self._check_and_resolve_alerts(product, tenant_id)
        
        await self.commit()
        
        logger.info(f"Stock ajustado: Producto {product_id}, De {stock_before} a {new_stock}")
        
        return movement
    
    async def _check_and_create_alerts(self, product: Product, tenant_id: int):
        """Verifica y crea alertas de stock si es necesario"""
        
        # Verificar si ya existe una alerta activa para este producto
        existing_alerts = await self.alert_repo.get_by_product(product.id, tenant_id)
        active_alerts = [a for a in existing_alerts if a.status == AlertStatus.ACTIVE]
        
        # Stock bajo
        if product.stock <= product.min_stock and product.stock > 0:
            # Verificar si ya existe alerta de stock bajo
            has_low_stock_alert = any(a.alert_type == AlertType.LOW_STOCK for a in active_alerts)
            
            if not has_low_stock_alert:
                alert_data = {
                    "tenant_id": tenant_id,
                    "product_id": product.id,
                    "alert_type": AlertType.LOW_STOCK,
                    "status": AlertStatus.ACTIVE,
                    "current_stock": product.stock,
                    "threshold_value": product.min_stock,
                    "message": f"Stock bajo para '{product.name}': {product.stock} unidades (mínimo: {product.min_stock})"
                }
                await self.alert_repo.create(alert_data)
                logger.warning(f"Alerta de stock bajo creada para producto {product.id}")
        
        # Sin stock
        elif product.stock <= 0:
            # Verificar si ya existe alerta de sin stock
            has_out_of_stock_alert = any(a.alert_type == AlertType.OUT_OF_STOCK for a in active_alerts)
            
            if not has_out_of_stock_alert:
                alert_data = {
                    "tenant_id": tenant_id,
                    "product_id": product.id,
                    "alert_type": AlertType.OUT_OF_STOCK,
                    "status": AlertStatus.ACTIVE,
                    "current_stock": product.stock,
                    "threshold_value": 0,
                    "message": f"Producto '{product.name}' sin stock"
                }
                await self.alert_repo.create(alert_data)
                logger.warning(f"Alerta de sin stock creada para producto {product.id}")
    
    async def _check_and_resolve_alerts(self, product: Product, tenant_id: int):
        """Verifica y resuelve alertas si el stock ha mejorado"""
        
        # Obtener alertas activas del producto
        existing_alerts = await self.alert_repo.get_by_product(product.id, tenant_id)
        active_alerts = [a for a in existing_alerts if a.status == AlertStatus.ACTIVE]
        
        for alert in active_alerts:
            # Resolver alerta de sin stock si ahora hay stock
            if alert.alert_type == AlertType.OUT_OF_STOCK and product.stock > 0:
                alert.resolve()
                logger.info(f"Alerta de sin stock resuelta para producto {product.id}")
            
            # Resolver alerta de stock bajo si el stock está por encima del mínimo
            elif alert.alert_type == AlertType.LOW_STOCK and product.stock > product.min_stock:
                alert.resolve()
                logger.info(f"Alerta de stock bajo resuelta para producto {product.id}")
