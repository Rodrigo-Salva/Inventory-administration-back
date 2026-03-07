from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import get_db
from ...dependencies import get_current_tenant
from ...repositories import CustomerRepository
from ...schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerOut,
    CustomerSummary
)
from ...core.pagination import PaginationParams, PaginatedResponse, create_pagination_metadata
from ...core.exceptions import DuplicateResourceException
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=PaginatedResponse[CustomerOut])
async def list_customers(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Buscar por nombre, documento o email"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los clientes con paginación y filtros"""
    repo = CustomerRepository(db)
    
    # Obtener clientes con filtros combinados
    customers, total = await repo.get_filtered(
        tenant_id=tenant_id,
        search=search,
        is_active=is_active,
        pagination=pagination
    )
    
    return PaginatedResponse(
        items=customers,
        metadata=create_pagination_metadata(
            total_items=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
    )


@router.post("/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer: CustomerCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo cliente"""
    repo = CustomerRepository(db)
    
    # Verificar si el documento ya existe (si se proporciona)
    if customer.document_number:
        existing = await repo.get_by_document(customer.document_number, tenant_id)
        if existing:
            raise DuplicateResourceException("Cliente", "document_number", customer.document_number)
    
    # Crear cliente
    customer_data = customer.model_dump()
    customer_data["tenant_id"] = tenant_id
    
    new_customer = await repo.create(customer_data)
    await db.commit()
    await db.refresh(new_customer)
    
    logger.info(f"Cliente creado: {new_customer.id} - {new_customer.name}")
    return new_customer


@router.get("/active", response_model=List[CustomerSummary])
async def get_active_customers(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene solo los clientes activos (para dropdowns)"""
    repo = CustomerRepository(db)
    customers = await repo.get_active_customers(tenant_id)
    return customers


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un cliente por ID"""
    repo = CustomerRepository(db)
    customer = await repo.get_by_id(customer_id, tenant_id)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente con ID {customer_id} no encontrado"
        )
    
    return customer


@router.put("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza un cliente"""
    repo = CustomerRepository(db)
    
    # Verificar que existe
    customer = await repo.get_by_id(customer_id, tenant_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente con ID {customer_id} no encontrado"
        )
    
    # Verificar documento único si se actualiza
    if customer_update.document_number and customer_update.document_number != customer.document_number:
        existing = await repo.get_by_document(customer_update.document_number, tenant_id)
        if existing and existing.id != customer_id:
            raise DuplicateResourceException("Cliente", "document_number", customer_update.document_number)
    
    # Actualizar
    update_data = customer_update.model_dump(exclude_unset=True)
    updated_customer = await repo.update(customer_id, update_data, tenant_id)
    await db.commit()
    await db.refresh(updated_customer)
    
    logger.info(f"Cliente actualizado: {customer_id}")
    return updated_customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Elimina un cliente (soft delete)"""
    repo = CustomerRepository(db)
    
    # Verificar que existe
    customer = await repo.get_by_id(customer_id, tenant_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente con ID {customer_id} no encontrado"
        )
    
    # Eliminar (soft delete)
    await repo.delete(customer_id, tenant_id)
    await db.commit()
    
    logger.info(f"Cliente eliminado: {customer_id}")
    return None
