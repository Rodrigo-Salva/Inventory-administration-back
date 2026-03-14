from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload, selectinload
from .base_repository import BaseRepository
from ..models.sale import Sale, SaleItem
from ..models.product import Product
from ..models.product_batch import ProductBatch
from ..models.inventory_movement import InventoryMovement, MovementType
from ..core.exceptions import ProductNotFoundException, InsufficientStockException
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from ..core.pagination import PaginationParams
from .credit_repo import CreditRepository
from ..models.loyalty import LoyaltyConfig, LoyaltyTransaction
from ..models.customer import Customer
from ..models.sale import PaymentMethod

class SaleRepository(BaseRepository[Sale]):
    def __init__(self, db: AsyncSession):
        super().__init__(Sale, db)

    async def get_by_id(self, id: int, tenant_id: Optional[int] = None) -> Optional[Sale]:
        """Obtiene una venta con sus items, productos, cliente y usuario cargados"""
        query = select(Sale).options(
            joinedload(Sale.items).joinedload(SaleItem.product),
            joinedload(Sale.customer),
            joinedload(Sale.user)
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
            
            # 4. Crear SaleItem con lote si aplica
            sale_item = SaleItem(
                sale_id=new_sale.id,
                product_id=product.id,
                batch_id=item_data.batch_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                subtotal=subtotal
            )
            sale_items.append(sale_item)
            
            # 4.1 Descontar de Lote si se especificó
            if item_data.batch_id:
                result_batch = await self.db.execute(
                    select(ProductBatch).where(ProductBatch.id == item_data.batch_id, ProductBatch.tenant_id == tenant_id)
                )
                batch = result_batch.scalar_one_or_none()
                if not batch:
                    raise Exception(f"Lote ID {item_data.batch_id} no encontrado")
                if batch.current_quantity < item_data.quantity:
                    raise InsufficientStockException(f"{product.name} (Lote: {batch.batch_number})", item_data.quantity, batch.current_quantity)
                
                batch.current_quantity -= item_data.quantity
            
            # 5. Actualizar stock del producto
            stock_before = product.stock
            product.stock -= item_data.quantity
            
            # 6. Registrar movimiento de inventario
            movement = InventoryMovement(
                tenant_id=tenant_id,
                product_id=product.id,
                batch_id=item_data.batch_id,
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

        # 7. Gestionar Redención de Puntos (Antes de calcular total final)
        discount_amount = Decimal(0)
        if sale_data.redeemed_points and sale_data.redeemed_points > 0 and sale_data.customer_id:
            # Obtener configuración y validar puntos del cliente
            cust_res = await self.db.execute(select(Customer).where(Customer.id == sale_data.customer_id))
            customer = cust_res.scalar_one_or_none()
            
            if not customer or customer.loyalty_points < sale_data.redeemed_points:
                raise Exception("El cliente no tiene puntos suficientes para redimir.")
            
            loyalty_res = await self.db.execute(
                select(LoyaltyConfig).where(LoyaltyConfig.tenant_id == tenant_id, LoyaltyConfig.is_active == True)
            )
            loyalty_config = loyalty_res.scalar_one_or_none()
            
            if not loyalty_config or sale_data.redeemed_points < loyalty_config.min_redemption_points:
                raise Exception(f"No se cumple el mínimo de puntos para redención ({loyalty_config.min_redemption_points if loyalty_config else 0}).")
            
            # Calcular monto de descuento
            discount_amount = Decimal(str(sale_data.redeemed_points)) * loyalty_config.amount_per_point
            
            # Asegurar que el descuento no supere el total
            if discount_amount > total_amount:
                discount_amount = total_amount
                # Ajustar puntos redimidos si el descuento superó el total
                # (Opcional: podrías preferir lanzar error si prefieres control estricto)
            
            # Aplicar descuento al total de la venta
            total_amount -= discount_amount
            
            # Actualizar puntos del cliente (restar)
            customer.loyalty_points -= sale_data.redeemed_points
            
            # Registrar transacción de redención
            redemption_trans = LoyaltyTransaction(
                tenant_id=tenant_id,
                customer_id=customer.id,
                sale_id=new_sale.id,
                points=-sale_data.redeemed_points,
                description=f"Puntos redimidos en venta #{new_sale.id}",
                transaction_type="redeem"
            )
            self.db.add(redemption_trans)
            
            # Guardar datos en la venta
            new_sale.redeemed_points = sale_data.redeemed_points
            new_sale.points_discount_amount = discount_amount

        # 8. Actualizar total de la venta
        new_sale.total_amount = total_amount
        new_sale.customer_id = sale_data.customer_id # Asegurar que el customer_id se asigne
        self.db.add_all(sale_items)
        
        # 8. Gestionar Crédito si el método de pago es CRÉDITO
        if sale_data.payment_method == PaymentMethod.CREDIT:
            if not sale_data.customer_id:
                raise Exception("Debe seleccionar un cliente para ventas a crédito.")
                
            credit_repo = CreditRepository(self.db)
            # Verificar disponibilidad
            if not await credit_repo.check_credit_availability(tenant_id, sale_data.customer_id, total_amount):
                raise Exception("El cliente no tiene cupo de crédito suficiente.")
            
            # Crear crédito
            await credit_repo.create_from_sale(
                tenant_id=tenant_id,
                customer_id=sale_data.customer_id,
                sale_id=new_sale.id,
                total_amount=total_amount
            )
        
        # 9. Gestionar Programa de Lealtad (Acumulación de puntos)
        if sale_data.customer_id:
            # Obtener configuración de lealtad
            loyalty_res = await self.db.execute(
                select(LoyaltyConfig).where(LoyaltyConfig.tenant_id == tenant_id, LoyaltyConfig.is_active == True)
            )
            loyalty_config = loyalty_res.scalar_one_or_none()
            
            if loyalty_config and loyalty_config.points_per_amount > 0:
                # Calcular puntos a ganar (ej: 1 punto por cada $100)
                points_to_earn = int(total_amount / loyalty_config.points_per_amount)
                
                if points_to_earn > 0:
                    # Actualizar puntos del cliente
                    cust_res = await self.db.execute(select(Customer).where(Customer.id == sale_data.customer_id))
                    customer = cust_res.scalar_one_or_none()
                    if customer:
                        customer.loyalty_points += points_to_earn
                        
                        # Registrar transacción
                        loyalty_trans = LoyaltyTransaction(
                            tenant_id=tenant_id,
                            customer_id=customer.id,
                            sale_id=new_sale.id,
                            points=points_to_earn,
                            description=f"Puntos ganados por venta #{new_sale.id}",
                            transaction_type="earn"
                        )
                        self.db.add(loyalty_trans)
        
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

        # 3. Anular crédito asociado si existe
        from ..models.credit import Credit, CreditStatus
        credit_query = select(Credit).where(
            and_(Credit.sale_id == sale_id, Credit.tenant_id == tenant_id)
        )
        res_credit = await self.db.execute(credit_query)
        credit = res_credit.scalar_one_or_none()
        
        if credit and credit.status != CreditStatus.ANNULLED:
            # Revertir saldo en el cliente
            from ..models.customer import Customer
            cust_query = select(Customer).where(Customer.id == credit.customer_id)
            res_cust = await self.db.execute(cust_query)
            customer = res_cust.scalar_one()
            customer.current_balance -= credit.remaining_amount
            
            credit.status = CreditStatus.ANNULLED
        
        # 4. Revertir puntos de lealtad si se otorgaron
        loyalty_trans_query = select(LoyaltyTransaction).where(
            and_(LoyaltyTransaction.sale_id == sale_id, LoyaltyTransaction.transaction_type == "earn")
        )
        res_loyalty = await self.db.execute(loyalty_trans_query)
        loyalty_trans = res_loyalty.scalar_one_or_none()
        
        if loyalty_trans:
            # Descontar puntos al cliente
            cust_res = await self.db.execute(select(Customer).where(Customer.id == loyalty_trans.customer_id))
            customer = cust_res.scalar_one_or_none()
            if customer:
                customer.loyalty_points -= loyalty_trans.points
                
                # Registrar reversión
                reversion = LoyaltyTransaction(
                    tenant_id=tenant_id,
                    customer_id=customer.id,
                    sale_id=sale_id,
                    points=-loyalty_trans.points,
                    description=f"Puntos revertidos por anulación de venta #{sale_id}",
                    transaction_type="adjust"
                )
                self.db.add(reversion)
        
        # 5. Revertir puntos de lealtad REDIMIDOS si existen
        loyalty_redeem_query = select(LoyaltyTransaction).where(
            and_(LoyaltyTransaction.sale_id == sale_id, LoyaltyTransaction.transaction_type == "redeem")
        )
        res_redeem = await self.db.execute(loyalty_redeem_query)
        redeem_trans = res_redeem.scalar_one_or_none()
        
        if redeem_trans:
            # Re-sumar puntos al cliente
            cust_res = await self.db.execute(select(Customer).where(Customer.id == redeem_trans.customer_id))
            customer = cust_res.scalar_one_or_none()
            if customer:
                customer.loyalty_points += abs(redeem_trans.points)
                
                # Registrar reversión de redención
                reversion_red = LoyaltyTransaction(
                    tenant_id=tenant_id,
                    customer_id=customer.id,
                    sale_id=sale_id,
                    points=abs(redeem_trans.points),
                    description=f"Puntos devueltos por anulación de venta #{sale_id}",
                    transaction_type="adjust"
                )
                self.db.add(reversion_red)
        
        await self.db.commit()
        await self.db.refresh(sale)
        return sale

    async def get_sales_paginated(
        self, 
        tenant_id: int, 
        pagination: PaginationParams,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        payment_method: Optional[str] = None,
        search: Optional[str] = None,
        seller_id: Optional[int] = None
    ) -> tuple[List[Sale], int]:
        query = select(Sale).options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.customer),
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
        
        # Usar la utilidad paginate del sistema
        from ..core.pagination import paginate
        return await paginate(self.db, query, pagination, Sale)
