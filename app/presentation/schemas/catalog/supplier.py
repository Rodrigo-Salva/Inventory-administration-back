from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime


class SupplierBase(BaseModel):
    """Schema base para proveedores"""
    name: str = Field(..., min_length=1, max_length=200, description="Nombre del proveedor")
    code: str = Field(..., min_length=1, max_length=50, description="Código único del proveedor")
    tax_id: Optional[str] = Field(None, max_length=50, description="RUC, NIT, Tax ID, etc.")
    
    # Contacto
    contact_name: Optional[str] = Field(None, max_length=100, description="Nombre de contacto")
    email: Optional[EmailStr] = Field(None, description="Email del proveedor")
    phone: Optional[str] = Field(None, max_length=20, description="Teléfono")
    mobile: Optional[str] = Field(None, max_length=20, description="Móvil")
    
    # Dirección
    address: Optional[str] = Field(None, description="Dirección completa")
    city: Optional[str] = Field(None, max_length=100, description="Ciudad")
    state: Optional[str] = Field(None, max_length=100, description="Estado/Provincia")
    country: Optional[str] = Field(None, max_length=100, description="País")
    postal_code: Optional[str] = Field(None, max_length=20, description="Código postal")
    
    # Información adicional
    website: Optional[str] = Field(None, max_length=200, description="Sitio web")
    notes: Optional[str] = Field(None, description="Notas adicionales")
    is_active: bool = Field(default=True, description="Proveedor activo")
    
    @field_validator('name', 'code')
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('El campo no puede estar vacío')
        return v.strip()


class SupplierCreate(SupplierBase):
    """Schema para crear un proveedor"""
    pass


class SupplierUpdate(BaseModel):
    """Schema para actualizar un proveedor"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    tax_id: Optional[str] = Field(None, max_length=50)
    
    contact_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    mobile: Optional[str] = Field(None, max_length=20)
    
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    
    website: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    
    @field_validator('name', 'code')
    @classmethod
    def must_not_be_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError('El campo no puede estar vacío')
        return v.strip() if v else None


class SupplierOut(SupplierBase):
    """Schema para respuesta de proveedor"""
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    
    model_config = {"from_attributes": True}


class SupplierSummary(BaseModel):
    """Schema resumido para listados"""
    id: int
    name: str
    code: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    
    model_config = {"from_attributes": True}
