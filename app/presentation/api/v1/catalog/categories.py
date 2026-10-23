from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.catalog import admin_use_cases as uc
from app.application.catalog.admin_dto import CreateEntityCommand, DeleteEntityCommand, UpdateEntityCommand
from app.application.shared.pagination import PaginatedResponse, PaginationParams, create_pagination_metadata
from app.domain.catalog.errors import CategoryNotFoundError
from app.infrastructure.logging import get_logger
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User, UserRole
from app.infrastructure.persistence.repositories.catalog.category_repo import CategoryRepository
from app.presentation.api.v1.catalog.admin_deps import (
    get_create_category,
    get_delete_category,
    get_update_category,
)
from app.presentation.dependencies import get_current_tenant, require_role
from app.presentation.schemas.catalog.category import (
    CategoryCreate,
    CategoryOut,
    CategoryTree,
    CategoryUpdate,
)

logger = get_logger(__name__)
router = APIRouter()

ADMIN_OR_MANAGER = [UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPERADMIN]


async def _category_or_404(db: AsyncSession, category_id: int, tenant_id: int):
    category = await CategoryRepository(db).get_by_id(category_id, tenant_id)
    if not category:
        raise CategoryNotFoundError()
    return category


@router.get("/", response_model=PaginatedResponse[CategoryOut])
async def list_categories(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Buscar por nombre o código"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Lista todas las categorías con paginación y filtros"""
    items, total = await CategoryRepository(db).get_filtered(
        tenant_id=tenant_id, search=search, is_active=is_active, pagination=pagination
    )
    return PaginatedResponse(
        items=items, metadata=create_pagination_metadata(pagination.page, pagination.page_size, total)
    )


@router.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    current_user: User = Depends(require_role(ADMIN_OR_MANAGER)),
    use_case: uc.CreateCategory = Depends(get_create_category),
    db: AsyncSession = Depends(get_db),
):
    """Crea una nueva categoría (Solo Admins/Managers)"""
    category_id = await use_case.execute(CreateEntityCommand(current_user.tenant_id, category.model_dump()))
    logger.info(f"Categoría creada: {category_id}")
    return await _category_or_404(db, category_id, current_user.tenant_id)


@router.get("/root", response_model=List[CategoryOut])
async def get_root_categories(tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    """Obtiene solo las categorías raíz (sin padre)"""
    return await CategoryRepository(db).get_root_categories(tenant_id)


@router.get("/tree", response_model=List[CategoryTree])
async def get_category_tree(
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Árbol jerárquico completo de categorías con filtro de estado"""
    all_categories, _ = await CategoryRepository(db).get_filtered(tenant_id=tenant_id, is_active=is_active)
    by_id = {c.id: c for c in all_categories}
    return [
        _build_tree_node(c, by_id)
        for c in all_categories
        if c.parent_id is None or c.parent_id not in by_id  # raíz, o su padre fue filtrado
    ]


def _build_tree_node(category, by_id: dict, _seen: frozenset = frozenset()) -> CategoryTree:
    """Construye un nodo del árbol; `_seen` protege contra ciclos heredados en los datos."""
    seen = _seen | {category.id}
    children = [
        _build_tree_node(child, by_id, seen)
        for child in by_id.values()
        if child.parent_id == category.id and child.id not in seen
    ]
    return CategoryTree(
        id=category.id, name=category.name, code=category.code, description=category.description,
        parent_id=category.parent_id, display_order=category.display_order, children=children,
    )


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(
    category_id: int, tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)
):
    """Obtiene una categoría por ID"""
    return await _category_or_404(db, category_id, tenant_id)


@router.get("/{category_id}/children", response_model=List[CategoryOut])
async def get_category_children(
    category_id: int, tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)
):
    """Obtiene las subcategorías de una categoría"""
    await _category_or_404(db, category_id, tenant_id)
    return await CategoryRepository(db).get_children(category_id, tenant_id)


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    current_user: User = Depends(require_role(ADMIN_OR_MANAGER)),
    use_case: uc.UpdateCategory = Depends(get_update_category),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza una categoría (Solo Admins/Managers); rechaza ciclos en la jerarquía"""
    await use_case.execute(
        UpdateEntityCommand(current_user.tenant_id, category_id, category_update.model_dump(exclude_unset=True))
    )
    return await _category_or_404(db, category_id, current_user.tenant_id)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    current_user: User = Depends(require_role(ADMIN_OR_MANAGER)),
    use_case: uc.DeleteCategory = Depends(get_delete_category),
):
    """Elimina una categoría (borrado lógico) si no tiene subcategorías"""
    await use_case.execute(DeleteEntityCommand(current_user.tenant_id, category_id))
    return None
