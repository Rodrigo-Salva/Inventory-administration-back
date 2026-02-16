from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import get_db
from ...dependencies import get_current_tenant
from ...repositories import CategoryRepository
from ...schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryOut,
    CategoryWithChildren,
    CategoryTree
)
from ...core.pagination import PaginationParams, PaginatedResponse, create_pagination_metadata
from ...core.exceptions import CategoryNotFoundException, DuplicateResourceException
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=PaginatedResponse[CategoryOut])
async def list_categories(
    pagination: PaginationParams = Depends(),
    parent_id: Optional[int] = Query(None, description="Filtrar por categoría padre"),
    search: Optional[str] = Query(None, description="Buscar por nombre o código"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista todas las categorías con paginación y filtros"""
    repo = CategoryRepository(db)
    
    # Construir filtros
    filters = {}
    if parent_id is not None:
        filters["parent_id"] = parent_id
    
    # Obtener categorías
    categories, total = await repo.get_paginated(pagination, tenant_id, filters)
    
    # Si hay búsqueda, filtrar en memoria (o mejorar el repo para búsqueda)
    if search:
        search_lower = search.lower()
        categories = [
            c for c in categories 
            if search_lower in c.name.lower() or (c.code and search_lower in c.code.lower())
        ]
        total = len(categories)
    
    return PaginatedResponse(
        items=categories,
        metadata=create_pagination_metadata(
            total_items=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
    )


@router.post("/", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Crea una nueva categoría"""
    repo = CategoryRepository(db)
    
    # Verificar si el código ya existe
    if category.code:
        existing = await repo.get_by_code(category.code, tenant_id)
        if existing:
            raise DuplicateResourceException(f"Ya existe una categoría con el código '{category.code}'")
    
    # Verificar que el padre existe si se proporciona
    if category.parent_id:
        parent = await repo.get_by_id(category.parent_id, tenant_id)
        if not parent:
            raise CategoryNotFoundException(f"Categoría padre con ID {category.parent_id} no encontrada")
    
    # Crear categoría
    category_data = category.model_dump()
    category_data["tenant_id"] = tenant_id
    
    new_category = await repo.create(category_data)
    await db.commit()
    await db.refresh(new_category)
    
    logger.info(f"Categoría creada: {new_category.id} - {new_category.name}")
    return new_category


@router.get("/root", response_model=List[CategoryOut])
async def get_root_categories(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene solo las categorías raíz (sin padre)"""
    repo = CategoryRepository(db)
    categories = await repo.get_root_categories(tenant_id)
    return categories


@router.get("/tree", response_model=List[CategoryTree])
async def get_category_tree(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el árbol jerárquico completo de categorías"""
    repo = CategoryRepository(db)
    
    # Obtener todas las categorías
    all_categories = await repo.get_hierarchy(tenant_id)
    
    # Construir árbol
    category_dict = {cat.id: cat for cat in all_categories}
    tree = []
    
    for category in all_categories:
        if category.parent_id is None:
            # Es una categoría raíz
            tree.append(_build_tree_node(category, category_dict))
    
    return tree


def _build_tree_node(category, category_dict: dict) -> CategoryTree:
    """Construye un nodo del árbol recursivamente"""
    children = [
        _build_tree_node(child, category_dict)
        for child in category_dict.values()
        if child.parent_id == category.id
    ]
    
    return CategoryTree(
        id=category.id,
        name=category.name,
        code=category.code,
        description=category.description,
        parent_id=category.parent_id,
        display_order=category.display_order,
        children=children
    )


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(
    category_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene una categoría por ID"""
    repo = CategoryRepository(db)
    category = await repo.get_by_id(category_id, tenant_id)
    
    if not category:
        raise CategoryNotFoundException(f"Categoría con ID {category_id} no encontrada")
    
    return category


@router.get("/{category_id}/children", response_model=List[CategoryOut])
async def get_category_children(
    category_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene las subcategorías de una categoría"""
    repo = CategoryRepository(db)
    
    # Verificar que la categoría existe
    category = await repo.get_by_id(category_id, tenant_id)
    if not category:
        raise CategoryNotFoundException(f"Categoría con ID {category_id} no encontrada")
    
    # Obtener hijos
    children = await repo.get_children(category_id, tenant_id)
    return children


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza una categoría"""
    repo = CategoryRepository(db)
    
    # Verificar que existe
    category = await repo.get_by_id(category_id, tenant_id)
    if not category:
        raise CategoryNotFoundException(f"Categoría con ID {category_id} no encontrada")
    
    # Validar que no se haga padre de sí misma
    if category_update.parent_id == category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Una categoría no puede ser su propio padre"
        )
    
    # Verificar código único si se actualiza
    if category_update.code and category_update.code != category.code:
        existing = await repo.get_by_code(category_update.code, tenant_id)
        if existing and existing.id != category_id:
            raise DuplicateResourceException(f"Ya existe una categoría con el código '{category_update.code}'")
    
    # Verificar que el nuevo padre existe
    if category_update.parent_id:
        parent = await repo.get_by_id(category_update.parent_id, tenant_id)
        if not parent:
            raise CategoryNotFoundException(f"Categoría padre con ID {category_update.parent_id} no encontrada")
        
        # TODO: Verificar que no se cree un ciclo en la jerarquía
    
    # Actualizar
    update_data = category_update.model_dump(exclude_unset=True)
    updated_category = await repo.update(category_id, tenant_id, update_data)
    await db.commit()
    await db.refresh(updated_category)
    
    logger.info(f"Categoría actualizada: {category_id}")
    return updated_category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Elimina una categoría (soft delete)"""
    repo = CategoryRepository(db)
    
    # Verificar que existe
    category = await repo.get_by_id(category_id, tenant_id)
    if not category:
        raise CategoryNotFoundException(f"Categoría con ID {category_id} no encontrada")
    
    # Verificar si tiene hijos
    children = await repo.get_children(category_id, tenant_id)
    if children:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar la categoría porque tiene {len(children)} subcategorías"
        )
    
    # TODO: Verificar si tiene productos asociados y advertir
    
    # Eliminar (soft delete)
    await repo.delete(category_id, tenant_id)
    await db.commit()
    
    logger.info(f"Categoría eliminada: {category_id}")
    return None
