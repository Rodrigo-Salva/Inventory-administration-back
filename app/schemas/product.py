from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime


# Base Schemas
class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., min_length=1, max_length=50)
    barcode: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    cost: Optional[Decimal] = Field(None, ge=0)
    stock: int = Field(default=0, ge=0)
    min_stock: int = Field(default=10, ge=0)
    max_stock: Optional[int] = Field(None, ge=0)
    weight: Optional[float] = Field(None, ge=0)
    dimensions: Optional[str] = Field(None, max_length=50)
    is_active: bool = True
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None


class ProductCreate(ProductBase):
    """Schema para crear un producto"""
    pass


class ProductUpdate(BaseModel):
    """Schema para actualizar un producto"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    barcode: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    cost: Optional[Decimal] = Field(None, ge=0)
    min_stock: Optional[int] = Field(None, ge=0)
    max_stock: Optional[int] = Field(None, ge=0)
    weight: Optional[float] = Field(None, ge=0)
    dimensions: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None


class ProductOut(ProductBase):
    """Schema de salida para producto"""
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProductWithRelations(ProductOut):
    """Producto con relaciones cargadas"""
    category: Optional["CategoryOut"] = None
    supplier: Optional["SupplierOut"] = None
    
    model_config = ConfigDict(from_attributes=True)


# Category Schemas
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[int] = None
    display_order: int = 0


class CategoryCreate(CategoryBase):
    """Schema para crear una categoría"""
    pass


class CategoryUpdate(BaseModel):
    """Schema para actualizar una categoría"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[int] = None
    display_order: Optional[int] = None


class CategoryOut(CategoryBase):
    """Schema de salida para categoría"""
    id: int
    tenant_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Supplier Schemas
class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)
    tax_id: Optional[str] = Field(None, max_length=50)
    contact_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    mobile: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    payment_terms: Optional[str] = Field(None, max_length=100)
    credit_limit: Optional[int] = Field(None, ge=0)
    is_active: bool = True
    notes: Optional[str] = None


class SupplierCreate(SupplierBase):
    """Schema para crear un proveedor"""
    pass


class SupplierUpdate(BaseModel):
    """Schema para actualizar un proveedor"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    tax_id: Optional[str] = Field(None, max_length=50)
    contact_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    mobile: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    payment_terms: Optional[str] = Field(None, max_length=100)
    credit_limit: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class SupplierOut(SupplierBase):
    """Schema de salida para proveedor"""
    id: int
    tenant_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Inventory Movement Schemas
class InventoryMovementBase(BaseModel):
    product_id: int
    quantity: int
    unit_cost: Optional[Decimal] = None
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class AddStockRequest(BaseModel):
    """Request para agregar stock"""
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_cost: Optional[Decimal] = Field(None, ge=0)
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class RemoveStockRequest(BaseModel):
    """Request para remover stock"""
    product_id: int
    quantity: int = Field(..., gt=0)
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    allow_negative: bool = False


class AdjustStockRequest(BaseModel):
    """Request para ajustar stock"""
    product_id: int
    new_stock: int = Field(..., ge=0)
    reason: Optional[str] = None


class InventoryMovementOut(BaseModel):
    """Schema de salida para movimiento de inventario"""
    id: int
    tenant_id: int
    product_id: int
    user_id: Optional[int]
    movement_type: str
    quantity: int
    stock_before: int
    stock_after: int
    unit_cost: Optional[Decimal]
    reference: Optional[str]
    notes: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Stock Alert Schemas
class StockAlertOut(BaseModel):
    """Schema de salida para alerta de stock"""
    id: int
    tenant_id: int
    product_id: int
    alert_type: str
    status: str
    current_stock: int
    threshold_value: Optional[int]
    message: Optional[str]
    is_notified: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Bulk Import Schemas
class BulkProductImport(BaseModel):
    """Schema para importación masiva de productos"""
    products: List[ProductCreate]


class BulkImportResponse(BaseModel):
    """Respuesta de importación masiva"""
    created: int
    skipped: int
    errors: List[str] = []


# Para evitar errores de forward reference
ProductWithRelations.model_rebuild()