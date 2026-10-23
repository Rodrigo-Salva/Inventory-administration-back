from datetime import datetime
from typing import Any, Protocol


class DashboardReader(Protocol):
    """Consultas agregadas que alimentan el dashboard (las implementa ReportRepository)."""

    async def get_dashboard_stats(self, tenant_id: int, start_date=None, end_date=None) -> dict: ...
    async def get_sales_stats(self, tenant_id: int, start_date=None, end_date=None) -> dict: ...
    async def get_purchase_stats(self, tenant_id: int, start_date=None, end_date=None) -> dict: ...
    async def get_movement_trends(self, tenant_id: int, start_date=None, end_date=None) -> list: ...
    async def get_sales_trends(self, tenant_id: int) -> list: ...
    async def get_purchase_trends(self, tenant_id: int) -> list: ...
    async def get_top_selling_products(self, tenant_id: int) -> list: ...
    async def get_recent_movements(self, tenant_id: int) -> list: ...
    async def get_low_stock_products(self, tenant_id: int) -> list: ...
    async def get_category_distribution(self, tenant_id: int) -> list: ...
    async def get_supplier_distribution(self, tenant_id: int) -> list: ...
    async def get_user_activity(self, tenant_id: int, start_date=None, end_date=None) -> list: ...
    async def get_top_moving_products(self, tenant_id: int, start_date=None, end_date=None) -> list: ...


async def build_dashboard(
    reader: DashboardReader,
    tenant_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    """Ensambla el dashboard: KPIs, tendencias y comparativa ventas vs compras."""
    stats = await reader.get_dashboard_stats(tenant_id, start_date=start_date, end_date=end_date)
    sales_stats = await reader.get_sales_stats(tenant_id, start_date=start_date, end_date=end_date)
    purchase_stats = await reader.get_purchase_stats(tenant_id, start_date=start_date, end_date=end_date)
    stats.update(
        {
            "sales_count": sales_stats["sales_count"],
            "total_revenue": sales_stats["total_revenue"],
            "purchase_count": purchase_stats["purchase_count"],
            "total_investment": purchase_stats["total_investment"],
        }
    )

    sales_trends = await reader.get_sales_trends(tenant_id)
    purchase_trends = await reader.get_purchase_trends(tenant_id)
    sales_by_date = {t["date"]: t["revenue"] for t in sales_trends}
    purchases_by_date = {t["date"]: t["investment"] for t in purchase_trends}
    comparison = [
        {"date": d, "sales": sales_by_date.get(d, 0), "purchases": purchases_by_date.get(d, 0)}
        for d in sorted(set(sales_by_date) | set(purchases_by_date))
    ]

    return {
        "stats": stats,
        "trends": await reader.get_movement_trends(tenant_id, start_date=start_date, end_date=end_date),
        "sales_trends": sales_trends,
        "purchase_trends": [
            {"date": t["date"], "revenue": t["investment"], "count": t["count"]} for t in purchase_trends
        ],
        "comparison_trends": comparison,
        "top_selling_products": await reader.get_top_selling_products(tenant_id),
        "recent_movements": await reader.get_recent_movements(tenant_id),
        "low_stock_products": await reader.get_low_stock_products(tenant_id),
        "category_distribution": await reader.get_category_distribution(tenant_id),
        "supplier_distribution": await reader.get_supplier_distribution(tenant_id),
        "user_activity": await reader.get_user_activity(tenant_id, start_date=start_date, end_date=end_date),
        "top_moving_products": await reader.get_top_moving_products(
            tenant_id, start_date=start_date, end_date=end_date
        ),
    }
