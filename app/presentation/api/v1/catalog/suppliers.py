from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.catalog import admin_use_cases as uc
from app.application.catalog.admin_dto import CreateEntityCommand, DeleteEntityCommand, UpdateEntityCommand
from app.application.shared.pagination import PaginatedResponse, PaginationParams, create_pagination_metadata
from app.domain.catalog.errors import SupplierNotFoundError
from app.infrastructure.logging import get_logger
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.catalog.supplier_repo import SupplierRepository
from app.presentation.api.v1.catalog.admin_deps import (
    get_create_supplier,
    get_delete_supplier,
    get_toggle_supplier,
    get_update_supplier,
)
from app.presentation.dependencies import get_current_tenant
from app.presentation.schemas.catalog.supplier import (
    SupplierCreate,
    SupplierOut,
    SupplierSummary,
    SupplierUpdate,
)

logger = get_logger(__name__)
router = APIRouter()


async def _supplier_or_404(db: AsyncSession, supplier_id: int, tenant_id: int):
    supplier = await SupplierRepository(db).get_by_id(supplier_id, tenant_id)
    if not supplier:
        raise SupplierNotFoundError()
    return supplier


@router.get("/", response_model=PaginatedResponse[SupplierOut])
async def list_suppliers(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Buscar por nombre, código o email"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los proveedores con paginación y filtros"""
    suppliers, total = await SupplierRepository(db).get_filtered(
        tenant_id=tenant_id, search=search, is_active=is_active, pagination=pagination
    )
    return PaginatedResponse(
        items=suppliers,
        metadata=create_pagination_metadata(total_items=total, page=pagination.page, page_size=pagination.page_size),
    )


@router.post("/", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    supplier: SupplierCreate,
    tenant_id: int = Depends(get_current_tenant),
    use_case: uc.CreateSupplier = Depends(get_create_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Crea un nuevo proveedor"""
    supplier_id = await use_case.execute(CreateEntityCommand(tenant_id, supplier.model_dump()))
    logger.info(f"Proveedor creado: {supplier_id}")
    return await _supplier_or_404(db, supplier_id, tenant_id)


@router.get("/active", response_model=List[SupplierSummary])
async def get_active_suppliers(tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    """Proveedores activos (para selectores)"""
    return await SupplierRepository(db).get_active_suppliers(tenant_id)


@router.get("/search", response_model=List[SupplierOut])
async def search_suppliers(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    limit: int = Query(10, ge=1, le=50, description="Límite de resultados"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Busca proveedores por nombre, código o email"""
    suppliers, _ = await SupplierRepository(db).search(q, tenant_id, PaginationParams(page=1, page_size=limit))
    return suppliers


@router.get("/{supplier_id}", response_model=SupplierOut)
async def get_supplier(
    supplier_id: int, tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)
):
    """Obtiene un proveedor por ID"""
    return await _supplier_or_404(db, supplier_id, tenant_id)


@router.put("/{supplier_id}", response_model=SupplierOut)
async def update_supplier(
    supplier_id: int,
    supplier_update: SupplierUpdate,
    tenant_id: int = Depends(get_current_tenant),
    use_case: uc.UpdateSupplier = Depends(get_update_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza un proveedor"""
    await use_case.execute(UpdateEntityCommand(tenant_id, supplier_id, supplier_update.model_dump(exclude_unset=True)))
    return await _supplier_or_404(db, supplier_id, tenant_id)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: int,
    tenant_id: int = Depends(get_current_tenant),
    use_case: uc.DeleteSupplier = Depends(get_delete_supplier),
):
    """Elimina un proveedor (borrado lógico)"""
    await use_case.execute(DeleteEntityCommand(tenant_id, supplier_id))
    return None


@router.patch("/{supplier_id}/toggle-active", response_model=SupplierOut)
async def toggle_supplier_active(
    supplier_id: int,
    tenant_id: int = Depends(get_current_tenant),
    use_case: uc.ToggleSupplierActive = Depends(get_toggle_supplier),
    db: AsyncSession = Depends(get_db),
):
    """Activa/desactiva un proveedor"""
    await use_case.execute(DeleteEntityCommand(tenant_id, supplier_id))
    return await _supplier_or_404(db, supplier_id, tenant_id)
