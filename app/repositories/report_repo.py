from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from ..models import Product, InventoryMovement, MovementType, Category
from typing import Dict, List, Any, Optional

class ReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_stats(self, tenant_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
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
        
        # 2. Movimientos en el rango (entradas/salidas)
        movements_conditions = [InventoryMovement.tenant_id == tenant_id]
        if start_date:
            movements_conditions.append(InventoryMovement.created_at >= start_date)
        if end_date:
            movements_conditions.append(InventoryMovement.created_at <= end_date)
        else:
            if not start_date:
                movements_conditions.append(InventoryMovement.created_at >= datetime.utcnow() - timedelta(days=30))

        movements_query = select(
            func.count(InventoryMovement.id).label("count"),
            InventoryMovement.movement_type
        ).where(and_(*movements_conditions)).group_by(InventoryMovement.movement_type)
        
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

    async def get_movement_trends(self, tenant_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Obtiene tendencias de movimientos en un rango de fechas"""
        
        conditions = [InventoryMovement.tenant_id == tenant_id]
        if start_date:
            conditions.append(InventoryMovement.created_at >= start_date)
        if end_date:
            conditions.append(InventoryMovement.created_at <= end_date)
        else:
            if not start_date:
                conditions.append(InventoryMovement.created_at >= datetime.utcnow() - timedelta(days=7))
        
        query = select(
            func.date(InventoryMovement.created_at).label("day"),
            func.count(InventoryMovement.id).label("count"),
            InventoryMovement.movement_type
        ).where(and_(*conditions)).group_by(
            func.date(InventoryMovement.created_at),
            InventoryMovement.movement_type
        ).order_by("day")
        
        result = await self.db.execute(query)
        rows = result.all()
        
        trends_map = {}
        for row in rows:
            day_str = str(row.day)
            if day_str not in trends_map:
                trends_map[day_str] = {"date": day_str, "entries": 0, "exits": 0}
            
            if row.movement_type in [MovementType.ENTRY, MovementType.INITIAL]:
                trends_map[day_str]["entries"] += row.count
            elif row.movement_type == MovementType.EXIT:
                trends_map[day_str]["exits"] += row.count
                
        return sorted(list(trends_map.values()), key=lambda x: x["date"])

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

    async def get_supplier_distribution(self, tenant_id: int) -> List[Dict[str, Any]]:
        """Obtiene la distribución de unidades por proveedor"""
        from ..models import Supplier
        query = select(
            Supplier.name,
            func.sum(Product.stock).label("units")
        ).join(Product, Product.supplier_id == Supplier.id
        ).where(and_(
            Product.tenant_id == tenant_id,
            Product.is_deleted == False
        )).group_by(Supplier.name)
        
        result = await self.db.execute(query)
        rows = result.all()
        return [{"name": row.name, "value": int(row.units or 0)} for row in rows]

    async def get_user_activity(self, tenant_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Obtiene actividad de movimientos por usuario"""
        from ..models import User
        conditions = [InventoryMovement.tenant_id == tenant_id]
        if start_date:
            conditions.append(InventoryMovement.created_at >= start_date)
        if end_date:
            conditions.append(InventoryMovement.created_at <= end_date)

        query = select(
            User.email,
            func.count(InventoryMovement.id).label("count")
        ).join(InventoryMovement, InventoryMovement.user_id == User.id
        ).where(and_(*conditions)).group_by(User.email).order_by(desc("count"))
        
        result = await self.db.execute(query)
        rows = result.all()
        return [{"name": row.email.split('@')[0], "value": row.count} for row in rows]

    async def get_top_moving_products(self, tenant_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Productos con más movimientos registrados"""
        conditions = [InventoryMovement.tenant_id == tenant_id]
        if start_date:
            conditions.append(InventoryMovement.created_at >= start_date)
        if end_date:
            conditions.append(InventoryMovement.created_at <= end_date)

        query = select(
            Product.name,
            func.count(InventoryMovement.id).label("total_moves")
        ).join(InventoryMovement, InventoryMovement.product_id == Product.id
        ).where(and_(*conditions)).group_by(Product.name).order_by(desc("total_moves")).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        return [{"name": row.name, "value": row.total_moves} for row in rows]

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
