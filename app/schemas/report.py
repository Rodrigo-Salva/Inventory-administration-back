from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime

class DashboardStats(BaseModel):
    total_products: int
    low_stock_count: int
    active_products: int
    total_inventory_value: float
    entries_count: int
    exits_count: int

class MovementTrend(BaseModel):
    date: str
    entries: int
    exits: int

class CategoryValue(BaseModel):
    name: str
    value: float

class InventoryReport(BaseModel):
    stats: DashboardStats
    trends: List[MovementTrend]
    recent_movements: List[Dict[str, Any]]
    low_stock_products: List[Dict[str, Any]] = []
    category_distribution: List[CategoryValue] = []
    supplier_distribution: List[CategoryValue] = []
    user_activity: List[CategoryValue] = []
    top_moving_products: List[CategoryValue] = []

    model_config = ConfigDict(from_attributes=True)
