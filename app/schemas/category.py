from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class CategoryBase(BaseModel):
    """Schema base para categorías"""
    name: str = Field(..., min_length=1, max_length=100, description="Nombre de la categoría")
    code: Optional[str] = Field(None, max_length=50, description="Código único de la categoría")
    description: Optional[str] = Field(None, max_length=500, description="Descripción de la categoría")
    parent_id: Optional[int] = Field(None, description="ID de la categoría padre")
    display_order: int = Field(default=0, description="Orden de visualización")
    
    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('El nombre no puede estar vacío')
        return v.strip()


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
    
    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError('El nombre no puede estar vacío')
        return v.strip() if v else None


class CategoryOut(CategoryBase):
    """Schema para respuesta de categoría"""
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    
    # Propiedades calculadas (se agregarán en el endpoint si es necesario)
    full_path: Optional[str] = None
    level: Optional[int] = None
    
    model_config = {"from_attributes": True}


class CategoryWithChildren(CategoryOut):
    """Schema para categoría con sus hijos"""
    children: List['CategoryOut'] = []
    
    model_config = {"from_attributes": True}


class CategoryTree(BaseModel):
    """Schema para árbol jerárquico de categorías"""
    id: int
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    display_order: int
    children: List['CategoryTree'] = []
    
    model_config = {"from_attributes": True}


# Necesario para referencias recursivas
CategoryWithChildren.model_rebuild()
CategoryTree.model_rebuild()
