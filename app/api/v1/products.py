from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...models import get_db
from ...dependencies import get_current_tenant
from ...repositories import ProductRepository
from ...schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductOut,
    ProductWithRelations
)
from ...core.pagination import PaginationParams, PaginatedResponse, create_pagination_metadata
from ...core.exceptions import ProductNotFoundException, DuplicateResourceException
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=PaginatedResponse[ProductOut])
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None, description="Buscar por nombre, SKU o código de barras"),
    category_id: int = Query(None, description="Filtrar por categoría"),
    is_active: bool = Query(None, description="Filtrar por estado activo"),
    low_stock: bool = Query(False, description="Solo productos con stock bajo"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista productos con paginación y filtros"""
    try:
        repo = ProductRepository(db)
        pagination = PaginationParams(page=page, page_size=page_size)
        
        if low_stock:
            products = await repo.get_low_stock_products(tenant_id)
            total = len(products)
            # Aplicar paginación manual
            start = pagination.offset
            end = start + pagination.limit
            items = products[start:end]
        elif search:
            items, total = await repo.search(search, tenant_id, pagination)
        elif category_id:
            items, total = await repo.get_by_category(category_id, tenant_id, pagination)
        else:
            filters = {}
            if is_active is not None:
                filters["is_active"] = 1 if is_active else 0
            items, total = await repo.get_paginated(pagination, tenant_id, filters)
        
        metadata = create_pagination_metadata(page, page_size, total)
        
        return PaginatedResponse(items=items, metadata=metadata)
    except Exception as e:
        import traceback
        print(f"❌ ERROR EN LIST_PRODUCTS: {e}")
        traceback.print_exc()
        raise e


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo producto"""
    repo = ProductRepository(db)
    
    # Verificar si el SKU ya existe
    existing = await repo.get_by_sku(product_data.sku, tenant_id)
    if existing:
        raise DuplicateResourceException("Producto", "SKU", product_data.sku)
    
    # Verificar barcode si se proporciona
    if product_data.barcode:
        existing_barcode = await repo.get_by_barcode(product_data.barcode, tenant_id)
        if existing_barcode:
            raise DuplicateResourceException("Producto", "código de barras", product_data.barcode)
    
    # Crear producto
    product_dict = product_data.model_dump()
    product_dict["tenant_id"] = tenant_id
    product_dict["is_active"] = 1 if product_data.is_active else 0
    
    product = await repo.create(product_dict)
    await db.commit()
    await db.refresh(product)
    
    logger.info(f"Producto creado: {product.id} - {product.name}")
    
    return product


@router.get("/{product_id}", response_model=ProductWithRelations)
async def get_product(
    product_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un producto por ID"""
    repo = ProductRepository(db)
    product = await repo.get_by_id(product_id, tenant_id)
    
    if not product:
        raise ProductNotFoundException(product_id)
    
    return product


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza un producto"""
    repo = ProductRepository(db)
    
    # Verificar que el producto existe
    product = await repo.get_by_id(product_id, tenant_id)
    if not product:
        raise ProductNotFoundException(product_id)
    
    # Verificar barcode único si se está actualizando
    if product_data.barcode and product_data.barcode != product.barcode:
        existing_barcode = await repo.get_by_barcode(product_data.barcode, tenant_id)
        if existing_barcode and existing_barcode.id != product_id:
            raise DuplicateResourceException("Producto", "código de barras", product_data.barcode)
    
    # Actualizar
    update_dict = product_data.model_dump(exclude_unset=True)
    if "is_active" in update_dict:
        update_dict["is_active"] = 1 if update_dict["is_active"] else 0
    
    updated_product = await repo.update(product_id, update_dict, tenant_id)
    await db.commit()
    
    logger.info(f"Producto actualizado: {product_id}")
    
    return updated_product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Elimina un producto (soft delete)"""
    repo = ProductRepository(db)
    
    # Verificar que existe
    product = await repo.get_by_id(product_id, tenant_id)
    if not product:
        raise ProductNotFoundException(product_id)
    
    # Soft delete
    await repo.delete(product_id, tenant_id, soft=True)
    await db.commit()
    
    logger.info(f"Producto eliminado: {product_id}")
    
    return None


@router.get("/low-stock/list", response_model=List[ProductOut])
async def get_low_stock_products(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene productos con stock bajo"""
    repo = ProductRepository(db)
    products = await repo.get_low_stock_products(tenant_id)
    return products