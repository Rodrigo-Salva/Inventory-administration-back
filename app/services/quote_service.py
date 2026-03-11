from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from ..repositories.quote_repo import QuoteRepository
from ..repositories.sale_repo import SaleRepository
from ..models.quote import QuoteStatus
from ..schemas.sale import SaleCreate, SaleItemCreate
from ..models.sale import PaymentMethod

class QuoteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.quote_repo = QuoteRepository(db)
        self.sale_repo = SaleRepository(db)

    async def convert_to_sale(
        self, quote_id: int, tenant_id: int, user_id: int, payment_method: PaymentMethod = PaymentMethod.CASH
    ):
        """Convierte una cotización en una venta real descontando inventario"""
        quote = await self.quote_repo.get_by_id(quote_id, tenant_id)
        
        if not quote:
            raise HTTPException(status_code=404, detail="Cotización no encontrada")
            
        if quote.status == QuoteStatus.CONVERTED:
            raise HTTPException(status_code=400, detail="La cotización ya fue convertida a venta")
            
        if quote.status in [QuoteStatus.REJECTED]:
            raise HTTPException(status_code=400, detail="No se puede convertir una cotización rechazada")

        # Preparar datos para crear la venta
        sale_items = []
        for item in quote.items:
            sale_items.append(SaleItemCreate(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price
            ))
            
        sale_data = SaleCreate(
            customer_id=quote.customer_id,
            payment_method=payment_method,
            notes=f"Generada desde la Cotización #{quote.id}. {quote.notes or ''}".strip(),
            items=sale_items
        )
        
        # Ejecutar la creación de la venta usando el SaleRepository (esto ya descuenta stock)
        try:
            new_sale = await self.sale_repo.create_sale(tenant_id, user_id, sale_data)
        except Exception as e:
            # Re-lanzar excepciones de validación de negocio (ej. falta de stock)
            raise HTTPException(status_code=400, detail=str(e))
            
        # Actualizar el estado de la cotización
        await self.quote_repo.update(
            id=quote.id,
            obj_in={"status": QuoteStatus.CONVERTED.value, "sale_id": new_sale.id},
            tenant_id=tenant_id,
            user_id=user_id
        )
        await self.db.commit()
        
        return new_sale
