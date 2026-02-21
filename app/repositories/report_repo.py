from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from ..models import Product, InventoryMovement, MovementType, Category
from typing import Dict, List, Any

class ReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_stats(self, tenant_id: int) -> Dict[str, Any]:
        """Obtiene estadísticas globales para el dashboard"""
        
        # 1. Total de productos y stock bajo
        products_query = select(
            func.count(Product.id).label("total"),
            func.sum(case((Product.stock <= Product.min_stock, 1), else_=0)).label("low_stock"),
            func.sum(case((Product.is_active == True, 1), else_=0)).label("active"),
            func.sum(Product.stock * Product.price).label("inventory_value")
        ).where(and_(Product.tenant_id == tenant_id, Product.is_deleted == False))
        
        products_result = await self.db.execute(products_query)
        p_stats = products_result.one_or_none()
        
        # 2. Movimientos del último mes (entradas/salidas)
        last_month = datetime.utcnow() - timedelta(days=30)
        movements_query = select(
            func.count(InventoryMovement.id).label("count"),
            InventoryMovement.movement_type
        ).where(
            and_(
                InventoryMovement.tenant_id == tenant_id,
                InventoryMovement.created_at >= last_month
            )
        ).group_by(InventoryMovement.movement_type)
        
        movements_result = await self.db.execute(movements_query)
        m_rows = movements_result.all()
        
        entries = sum(row.count for row in m_rows if row.movement_type in [MovementType.ENTRY, MovementType.INITIAL])
        exits = sum(row.count for row in m_rows if row.movement_type == MovementType.EXIT)

        return {
            "total_products": p_stats.total or 0,
            "low_stock_count": p_stats.low_stock or 0,
            "active_products": p_stats.active or 0,
            "total_inventory_value": float(p_stats.inventory_value or 0),
            "entries_count": entries,
            "exits_count": exits
        }

    async def get_movement_trends(self, tenant_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Obtiene tendencias de movimientos de los últimos X días"""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Agrupar por día y tipo
        query = select(
            func.date(InventoryMovement.created_at).label("day"),
            func.count(InventoryMovement.id).label("count"),
            InventoryMovement.movement_type
        ).where(
            and_(
                InventoryMovement.tenant_id == tenant_id,
                InventoryMovement.created_at >= since
            )
        ).group_by(
            func.date(InventoryMovement.created_at),
            InventoryMovement.movement_type
        ).order_by("day")
        
        result = await self.db.execute(query)
        rows = result.all()
        
        # Procesar filas en un mapa
        trends_map = {}
        for row in rows:
            day_str = str(row.day)
            if day_str not in trends_map:
                trends_map[day_str] = {"date": day_str, "entries": 0, "exits": 0}
            
            if row.movement_type in [MovementType.ENTRY, MovementType.INITIAL]:
                trends_map[day_str]["entries"] += row.count
            elif row.movement_type == MovementType.EXIT:
                trends_map[day_str]["exits"] += row.count

        # Asegurar que todos los días en el rango tengan entrada (incluso si es 0)
        final_trends = []
        for i in range(days):
            d = (datetime.utcnow() - timedelta(days=i)).date()
            d_str = str(d)
            final_trends.append(trends_map.get(d_str, {"date": d_str, "entries": 0, "exits": 0}))
                
        return sorted(final_trends, key=lambda x: x["date"])

    async def get_category_distribution(self, tenant_id: int) -> List[Dict[str, Any]]:
        """Obtiene la distribución del valor del inventario por categoría"""
        query = select(
            Category.name,
            func.sum(Product.stock * Product.price).label("value")
        ).join(Product, Product.category_id == Category.id
        ).where(and_(
            Product.tenant_id == tenant_id,
            Product.is_deleted == False
        )).group_by(Category.name)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [{"name": row.name, "value": float(row.value or 0)} for row in rows]

    async def get_recent_movements(self, tenant_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Obtiene los movimientos más recientes con info de producto"""
        query = select(
            InventoryMovement,
            Product.name.label("product_name")
        ).join(Product, InventoryMovement.product_id == Product.id
        ).where(InventoryMovement.tenant_id == tenant_id
        ).order_by(desc(InventoryMovement.created_at)
        ).limit(limit)
        
        result = await self.db.execute(query)
        movements = []
        for row in result:
            m = row.InventoryMovement
            movements.append({
                "id": m.id,
                "product_name": row.product_name,
                "type": m.movement_type,
                "quantity": m.quantity,
                "created_at": m.created_at.isoformat()
            })
        return movements

    async def get_low_stock_products(self, tenant_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Obtiene productos que están bajo su stock mínimo"""
        query = select(Product).where(
            and_(
                Product.tenant_id == tenant_id,
                Product.is_deleted == False,
                Product.stock <= Product.min_stock,
                Product.is_active == True
            )
        ).order_by(Product.stock.asc()).limit(limit)
        
        result = await self.db.execute(query)
        products = result.scalars().all()
        
        return [
            {
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "stock": p.stock,
                "min_stock": p.min_stock
            } for p in products
        ]
