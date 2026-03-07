from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime


class CustomerBase(BaseModel):
    """Schema base para clientes"""
    name: str = Field(..., min_length=1, max_length=200, description="Nombre del cliente")
    document_type: Optional[str] = Field(None, max_length=50, description="Tipo de documento (DNI, RUC, etc.)")
    document_number: Optional[str] = Field(None, max_length=50, description="Número de documento")
    
    # Contacto
    email: Optional[EmailStr] = Field(None, description="Email del cliente")
    phone: Optional[str] = Field(None, max_length=20, description="Teléfono")
    
    # Dirección
    address: Optional[str] = Field(None, description="Dirección completa")
    city: Optional[str] = Field(None, max_length=100, description="Ciudad")
    state: Optional[str] = Field(None, max_length=100, description="Estado/Provincia")
    country: Optional[str] = Field(None, max_length=100, description="País")
    
    # Información adicional
    notes: Optional[str] = Field(None, description="Notas adicionales")
    is_active: bool = Field(default=True, description="Cliente activo")
    
    @field_validator('name')
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('El nombre no puede estar vacío')
        return v.strip()


class CustomerCreate(CustomerBase):
    """Schema para crear un cliente"""
    pass


class CustomerUpdate(BaseModel):
    """Schema para actualizar un cliente"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    document_type: Optional[str] = Field(None, max_length=50)
    document_number: Optional[str] = Field(None, max_length=50)
    
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    
    @field_validator('name')
    @classmethod
    def must_not_be_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError('El nombre no puede estar vacío')
        return v.strip() if v else None


class CustomerOut(CustomerBase):
    """Schema para respuesta de cliente"""
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    
    model_config = {"from_attributes": True}


class CustomerSummary(BaseModel):
    """Schema resumido para listados"""
    id: int
    name: str
    document_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    
    model_config = {"from_attributes": True}
