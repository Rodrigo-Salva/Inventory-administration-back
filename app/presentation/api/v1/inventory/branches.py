from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.catalog import admin_use_cases as uc
from app.application.catalog.admin_dto import CreateEntityCommand, DeleteEntityCommand, UpdateEntityCommand
from app.application.shared.pagination import PaginatedResponse, PaginationParams, create_pagination_metadata
from app.domain.inventory.errors import BranchNotFoundError
from app.infrastructure.logging import get_logger
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User
from app.infrastructure.persistence.repositories.inventory.branch_repo import BranchRepository
from app.presentation.api.v1.catalog.admin_deps import get_create_branch, get_delete_branch, get_update_branch
from app.presentation.dependencies import get_current_tenant, require_permission
from app.presentation.schemas.inventory.branch import BranchCreate, BranchResponse, BranchUpdate

logger = get_logger(__name__)
router = APIRouter()


async def _branch_or_404(db: AsyncSession, branch_id: int, tenant_id: int):
    branch = await BranchRepository(db).get_by_id(branch_id, tenant_id)
    if not branch:
        raise BranchNotFoundError()
    return branch


@router.get("", response_model=PaginatedResponse[BranchResponse])
async def list_branches(
    pagination: PaginationParams = Depends(),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_permission("branches:view")),
    db: AsyncSession = Depends(get_db),
):
    """Lista las sucursales con paginación"""
    items, total = await BranchRepository(db).get_paginated(pagination, tenant_id)
    return PaginatedResponse(
        items=items, metadata=create_pagination_metadata(pagination.page, pagination.page_size, total)
    )


@router.get("/active", response_model=List[BranchResponse])
async def list_active_branches(
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_permission("branches:view")),
    db: AsyncSession = Depends(get_db),
):
    """Sucursales activas (ideal para selects/combobox)"""
    return await BranchRepository(db).get_all_active(tenant_id)


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    branch_in: BranchCreate,
    current_user: User = Depends(require_permission("branches:create")),
    use_case: uc.CreateBranch = Depends(get_create_branch),
    db: AsyncSession = Depends(get_db),
):
    """Crea una nueva sucursal"""
    branch_id = await use_case.execute(
        CreateEntityCommand(current_user.tenant_id, branch_in.model_dump(), user_id=current_user.id)
    )
    logger.info(f"Sucursal creada: {branch_id}")
    return await _branch_or_404(db, branch_id, current_user.tenant_id)


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(
    branch_id: int,
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(require_permission("branches:view")),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene una sucursal por ID"""
    return await _branch_or_404(db, branch_id, tenant_id)


@router.put("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: int,
    branch_in: BranchUpdate,
    current_user: User = Depends(require_permission("branches:edit")),
    use_case: uc.UpdateBranch = Depends(get_update_branch),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza una sucursal"""
    await use_case.execute(
        UpdateEntityCommand(
            current_user.tenant_id, branch_id, branch_in.model_dump(exclude_unset=True), user_id=current_user.id
        )
    )
    return await _branch_or_404(db, branch_id, current_user.tenant_id)


@router.delete("/{branch_id}", status_code=status.HTTP_200_OK)
async def delete_branch(
    branch_id: int,
    current_user: User = Depends(require_permission("branches:delete")),
    use_case: uc.DeleteBranch = Depends(get_delete_branch),
):
    """Elimina una sucursal (borrado lógico; no se permite si aún tiene stock)"""
    await use_case.execute(DeleteEntityCommand(current_user.tenant_id, branch_id, user_id=current_user.id))
    return {"detail": "Sucursal eliminada"}
