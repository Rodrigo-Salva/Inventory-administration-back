from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import get_db
from ...dependencies import get_current_tenant
from ...repositories import SupplierRepository
from ...schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierOut,
    SupplierSummary
)
from ...core.pagination import PaginationParams, PaginatedResponse, create_pagination_metadata
from ...core.exceptions import SupplierNotFoundException, DuplicateResourceException
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=PaginatedResponse[SupplierOut])
async def list_suppliers(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Buscar por nombre, código o email"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los proveedores con paginación y filtros"""
    repo = SupplierRepository(db)
    
    # Si hay búsqueda, usar método de búsqueda
    if search:
        suppliers, total = await repo.search(search, tenant_id, pagination)
    else:
        # Construir filtros
        filters = {}
        if is_active is not None:
            filters["is_active"] = is_active
        
        # Obtener proveedores
        suppliers, total = await repo.get_paginated(pagination, tenant_id, filters)
    
    return PaginatedResponse(
        items=suppliers,
        metadata=create_pagination_metadata(
            total_items=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
    )


@router.post("/", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    supplier: SupplierCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo proveedor"""
    repo = SupplierRepository(db)
    
    # Verificar si el código ya existe
    existing = await repo.get_by_code(supplier.code, tenant_id)
    if existing:
        raise DuplicateResourceException("Proveedor", "code", supplier.code)
    
    # Crear proveedor
    supplier_data = supplier.model_dump()
    supplier_data["tenant_id"] = tenant_id
    
    new_supplier = await repo.create(supplier_data)
    await db.commit()
    await db.refresh(new_supplier)
    
    logger.info(f"Proveedor creado: {new_supplier.id} - {new_supplier.name}")
    return new_supplier


@router.get("/active", response_model=List[SupplierSummary])
async def get_active_suppliers(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene solo los proveedores activos (para dropdowns)"""
    repo = SupplierRepository(db)
    suppliers = await repo.get_active_suppliers(tenant_id)
    return suppliers


@router.get("/search", response_model=List[SupplierOut])
async def search_suppliers(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    limit: int = Query(10, ge=1, le=50, description="Límite de resultados"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Busca proveedores por nombre, código o email"""
    repo = SupplierRepository(db)
    
    # Crear paginación temporal
    from ...core.pagination import PaginationParams
    pagination = PaginationParams(page=1, size=limit)
    
    suppliers, _ = await repo.search(q, tenant_id, pagination)
    return suppliers


@router.get("/{supplier_id}", response_model=SupplierOut)
async def get_supplier(
    supplier_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un proveedor por ID"""
    repo = SupplierRepository(db)
    supplier = await repo.get_by_id(supplier_id, tenant_id)
    
    if not supplier:
        raise SupplierNotFoundException(supplier_id)
    
    return supplier


@router.put("/{supplier_id}", response_model=SupplierOut)
async def update_supplier(
    supplier_id: int,
    supplier_update: SupplierUpdate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza un proveedor"""
    repo = SupplierRepository(db)
    
    # Verificar que existe
    supplier = await repo.get_by_id(supplier_id, tenant_id)
    if not supplier:
        raise SupplierNotFoundException(supplier_id)
    
    # Verificar código único si se actualiza
    if supplier_update.code and supplier_update.code != supplier.code:
        existing = await repo.get_by_code(supplier_update.code, tenant_id)
        if existing and existing.id != supplier_id:
            raise DuplicateResourceException("Proveedor", "code", supplier_update.code)
    
    # Actualizar
    update_data = supplier_update.model_dump(exclude_unset=True)
    updated_supplier = await repo.update(supplier_id, tenant_id, update_data)
    await db.commit()
    await db.refresh(updated_supplier)
    
    logger.info(f"Proveedor actualizado: {supplier_id}")
    return updated_supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Elimina un proveedor (soft delete)"""
    repo = SupplierRepository(db)
    
    # Verificar que existe
    supplier = await repo.get_by_id(supplier_id, tenant_id)
    if not supplier:
        raise SupplierNotFoundException(supplier_id)
    
    # TODO: Verificar si tiene productos asociados y advertir
    
    # Eliminar (soft delete)
    await repo.delete(supplier_id, tenant_id)
    await db.commit()
    
    logger.info(f"Proveedor eliminado: {supplier_id}")
    return None


@router.patch("/{supplier_id}/toggle-active", response_model=SupplierOut)
async def toggle_supplier_active(
    supplier_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Activa/desactiva un proveedor"""
    repo = SupplierRepository(db)
    
    # Verificar que existe
    supplier = await repo.get_by_id(supplier_id, tenant_id)
    if not supplier:
        raise SupplierNotFoundException(supplier_id)
    
    # Cambiar estado
    new_state = not supplier.is_active
    updated_supplier = await repo.update(supplier_id, tenant_id, {"is_active": new_state})
    await db.commit()
    await db.refresh(updated_supplier)
    
    logger.info(f"Proveedor {supplier_id} {'activado' if new_state else 'desactivado'}")
    return updated_supplier
