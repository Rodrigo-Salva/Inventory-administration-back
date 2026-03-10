from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...models import get_db
from ...dependencies import get_current_tenant, get_current_user, require_permission
from ...models.user import User
from ...repositories.branch_repo import BranchRepository
from ...schemas.branch import (
    BranchCreate,
    BranchUpdate,
    BranchResponse
)
from ...core.pagination import PaginationParams, PaginatedResponse, create_pagination_metadata
from ...core.exceptions import ResourceNotFoundException
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("", response_model=PaginatedResponse[BranchResponse])
async def list_branches(
    pagination: PaginationParams = Depends(),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_permission("branches:view")),
    db: AsyncSession = Depends(get_db)
):
    """Lista las sucursales con paginación"""
    repo = BranchRepository(db)
    items, total = await repo.get_paginated(pagination, tenant_id)
    metadata = create_pagination_metadata(pagination.page, pagination.page_size, total)
    return PaginatedResponse(items=items, metadata=metadata)

@router.get("/active", response_model=List[BranchResponse])
async def list_active_branches(
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_permission("branches:view")),
    db: AsyncSession = Depends(get_db)
):
    """Lista todas las sucursales activas (ideal para selects/combobox)"""
    repo = BranchRepository(db)
    return await repo.get_all_active(tenant_id)

@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    branch_in: BranchCreate,
    current_user: User = Depends(require_permission("branches:create")),
    db: AsyncSession = Depends(get_db)
):
    """Crea una nueva sucursal (Requiere permisos de configuración)"""
    repo = BranchRepository(db)
    branch_dict = branch_in.model_dump()
    branch_dict["tenant_id"] = current_user.tenant_id
    
    branch = await repo.create(branch_dict, user_id=current_user.id)
    await db.commit()
    await db.refresh(branch)
    logger.info(f"Sucursal creada: {branch.id} - {branch.name}")
    return branch

@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(
    branch_id: int,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_permission("branches:view")),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene una sucursal por ID"""
    repo = BranchRepository(db)
    branch = await repo.get_by_id(branch_id, tenant_id)
    if not branch:
        raise ResourceNotFoundException("Sucursal", branch_id)
    return branch

@router.put("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: int,
    branch_in: BranchUpdate,
    current_user: User = Depends(require_permission("branches:edit")),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza una sucursal"""
    repo = BranchRepository(db)
    branch = await repo.get_by_id(branch_id, current_user.tenant_id)
    
    if not branch:
        raise ResourceNotFoundException("Sucursal", branch_id)
        
    update_dict = branch_in.model_dump(exclude_unset=True)
    updated_branch = await repo.update(branch_id, update_dict, current_user.tenant_id, user_id=current_user.id)
    await db.commit()
    await db.refresh(updated_branch)
    return updated_branch

@router.delete("/{branch_id}", status_code=status.HTTP_200_OK)
async def delete_branch(
    branch_id: int,
    current_user: User = Depends(require_permission("branches:delete")),
    db: AsyncSession = Depends(get_db)
):
    """Elimina una sucursal (soft delete)"""
    repo = BranchRepository(db)
    await repo.delete(branch_id, current_user.tenant_id, user_id=current_user.id)
    await db.commit()
    return {"detail": "Sucursal eliminada"}
