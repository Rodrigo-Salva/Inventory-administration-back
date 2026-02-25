from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from ..models import Product, InventoryMovement, MovementType, Category, Sale, SaleItem, User
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
    async def get_sales_stats(self, tenant_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Estadísticas de ventas para el dashboard"""
        conditions = [Sale.tenant_id == tenant_id, Sale.status == "completed"]
        if start_date: conditions.append(Sale.created_at >= start_date)
        if end_date: conditions.append(Sale.created_at <= end_date)
        else:
            if not start_date: conditions.append(Sale.created_at >= datetime.utcnow() - timedelta(days=30))

        query = select(
            func.count(Sale.id).label("total_sales"),
            func.sum(Sale.total_amount).label("total_revenue")
        ).where(and_(*conditions))
        
        result = await self.db.execute(query)
        row = result.one_or_none()
        
        return {
            "sales_count": row.total_sales or 0,
            "total_revenue": float(row.total_revenue or 0)
        }

    async def get_sales_trends(self, tenant_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Tendencia de ventas diaria"""
        start_date = datetime.utcnow() - timedelta(days=days)
        query = select(
            func.date(Sale.created_at).label("day"),
            func.sum(Sale.total_amount).label("revenue"),
            func.count(Sale.id).label("count")
        ).where(and_(
            Sale.tenant_id == tenant_id,
            Sale.status == "completed",
            Sale.created_at >= start_date
        )).group_by(func.date(Sale.created_at)).order_by("day")
        
        result = await self.db.execute(query)
        rows = result.all()
        return [{"date": str(row.day), "revenue": float(row.revenue or 0), "count": row.count} for row in rows]

    async def get_top_selling_products(self, tenant_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Productos más vendidos por cantidad"""
        query = select(
            Product.name,
            func.sum(SaleItem.quantity).label("total_sold")
        ).join(SaleItem, Product.id == SaleItem.product_id
        ).join(Sale, Sale.id == SaleItem.sale_id
        ).where(and_(
            Sale.tenant_id == tenant_id,
            Sale.status == "completed"
        )).group_by(Product.name).order_by(desc("total_sold")).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        return [{"name": row.name, "value": int(row.total_sold or 0)} for row in rows]

    async def get_filtered_sales(
        self, 
        tenant_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        payment_method: Optional[str] = None
    ) -> List[Sale]:
        """Obtiene ventas filtradas para reportes"""
        from sqlalchemy.orm import selectinload
        
        query = select(Sale).options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.user)
        ).where(Sale.tenant_id == tenant_id)

        if start_date: query = query.where(Sale.created_at >= start_date)
        if end_date: query = query.where(Sale.created_at <= end_date)
        if status: query = query.where(Sale.status == status)
        if payment_method: query = query.where(Sale.payment_method == payment_method)

        query = query.order_by(desc(Sale.created_at))
        
        result = await self.db.execute(query)
        return result.unique().scalars().all()

    async def get_sales_history_stats(
        self,
        tenant_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        payment_method: Optional[str] = None,
        search: Optional[str] = None,
        seller_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Metricas y tendencias del historial de ventas con filtros"""
        
        # 1. Build common filters
        filters = [Sale.tenant_id == tenant_id]
        if seller_id: filters.append(Sale.user_id == seller_id)
        if start_date: filters.append(Sale.created_at >= start_date)
        if end_date: filters.append(Sale.created_at <= end_date)
        if status: filters.append(Sale.status == status)
        if payment_method: filters.append(Sale.payment_method == payment_method)
        
        if search:
            if search.isdigit():
                filters.append(Sale.id == int(search))
            else:
                p_search = select(SaleItem.sale_id).join(Product).where(
                    and_(Product.tenant_id == tenant_id, Product.name.ilike(f"%{search}%"))
                )
                filters.append(Sale.id.in_(p_search))

        # 2. Metricas Generales (Directo de Sales)
        sales_q = select(
            func.count(Sale.id).label("total_count"),
            func.sum(func.coalesce(Sale.total_amount, 0)).label("total_revenue"),
            func.avg(func.coalesce(Sale.total_amount, 0)).label("avg_sale")
        ).where(and_(*filters))

        # 3. Metricas de Items (Join con SaleItem y Product)
        items_q = select(
            func.sum(func.coalesce(SaleItem.quantity, 0)).label("total_items"),
            func.sum(func.coalesce(SaleItem.quantity, 0) * func.coalesce(Product.cost, 0)).label("total_cogs")
        ).join(Sale, Sale.id == SaleItem.sale_id
        ).join(Product, SaleItem.product_id == Product.id, isouter=True
        ).where(and_(*filters))

        # 4. Tendencia
        trend_q = select(
            func.date(Sale.created_at).label("day"),
            func.count(Sale.id).label("count"),
            func.sum(func.coalesce(Sale.total_amount, 0)).label("revenue")
        ).where(and_(*filters)).group_by(func.date(Sale.created_at)).order_by("day")

        # 5. Metodos de pago
        payment_q = select(
            Sale.payment_method,
            func.sum(func.coalesce(Sale.total_amount, 0)).label("value")
        ).where(and_(*filters)).group_by(Sale.payment_method)

        # 6. Producto Estrella
        top_q = select(
            Product.name,
            func.sum(SaleItem.quantity).label("occurrences")
        ).join(SaleItem, Product.id == SaleItem.product_id
        ).join(Sale, Sale.id == SaleItem.sale_id
        ).where(and_(*filters)).group_by(Product.name).order_by(desc("occurrences")).limit(1)

        # 7. Distribución por Categoría
        category_q = select(
            Category.name,
            func.sum(SaleItem.subtotal).label("value")
        ).join(SaleItem, Product.id == SaleItem.product_id
        ).join(Product, Product.id == SaleItem.product_id
        ).join(Category, Category.id == Product.category_id
        ).join(Sale, Sale.id == SaleItem.sale_id
        ).where(and_(*filters)).group_by(Category.name)


        # Ejecutar todas
        sales_res = await self.db.execute(sales_q)
        items_res = await self.db.execute(items_q)
        trend_res = await self.db.execute(trend_q)
        payment_res = await self.db.execute(payment_q)
        top_res = await self.db.execute(top_q)
        category_res = await self.db.execute(category_q)

        s_stats = sales_res.one()
        i_stats = items_res.one()
        top_row = top_res.one_or_none()

        revenue = float(s_stats.total_revenue or 0)
        cogs = float(i_stats.total_cogs or 0)
        profit = revenue - cogs

        # Vendedores list
        sellers_q = select(User.id, User.email).join(Sale, User.id == Sale.user_id).where(Sale.tenant_id == tenant_id).distinct()
        sellers_res = await self.db.execute(sellers_q)
        sellers_list = [{"id": r.id, "email": r.email.split('@')[0]} for r in sellers_res.all()]

        # Stock bajo
        low_q = select(Product.id, Product.name, Product.stock, Product.min_stock).where(
            and_(Product.tenant_id == tenant_id, Product.is_active == True, Product.stock <= Product.min_stock)
        ).order_by(Product.stock.asc()).limit(5)
        low_res = await self.db.execute(low_q)
        low_list = [{"id": r.id, "name": r.name, "stock": r.stock, "min_stock": r.min_stock} for r in low_res.all()]

        return {
            "total_count": s_stats.total_count or 0,
            "total_revenue": revenue,
            "total_items": int(i_stats.total_items or 0),
            "avg_sale": float(s_stats.avg_sale or 0),
            "estimated_profit": profit,
            "profit_margin": (profit / revenue * 100) if revenue > 0 else 0,
            "top_product": top_row.name if top_row else "N/A",
            "trends": [{"date": str(row.day), "revenue": float(row.revenue or 0), "count": row.count} for row in trend_res.all()],
            "payment_distribution": [{"name": row.payment_method, "value": float(row.value or 0)} for row in payment_res.all()],
            "category_distribution": [{"name": row.name, "value": float(row.value or 0)} for row in category_res.all()],
            "sellers": sellers_list,
            "low_stock_items": low_list
        }
