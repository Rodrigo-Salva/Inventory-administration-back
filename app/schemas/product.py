from pydantic import BaseModel
from typing import Optional

class ProductCreate(BaseModel):
    name: str
    sku: str
    price: float
    description: Optional[str] = None
    min_stock: int = 10

class ProductOut(BaseModel):
    id: int
    name: str
    sku: str
    price: float
    stock: int
    min_stock: int
    
    class Config:
        from_attributes = True