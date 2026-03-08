from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from ...models import get_db
from ...dependencies import get_current_tenant, require_role, require_permission
from ...models.user import User, UserRole
import csv
import io
from decimal import Decimal
from ...repositories import ProductRepository
from ...schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductOut,
    ProductWithRelations,
    BulkProductImport,
    BulkImportResponse
)
from ...core.pagination import PaginationParams, PaginatedResponse, create_pagination_metadata
from ...core.exceptions import ProductNotFoundException, DuplicateResourceException
from ...core.logging_config import get_logger
from ...services.label_generator import LabelGenerator
from fastapi.responses import StreamingResponse
from datetime import datetime

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=PaginatedResponse[ProductWithRelations])
async def list_products(
    pagination: PaginationParams = Depends(),
    search: str = Query(None, description="Buscar por nombre, SKU o código de barras"),
    category_id: int = Query(None, description="Filtrar por categoría"),
    supplier_id: int = Query(None, description="Filtrar por proveedor"),
    is_active: bool = Query(None, description="Filtrar por estado activo"),
    low_stock: bool = Query(False, description="Solo productos con stock bajo"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Lista productos con paginación y filtros combinados"""
    try:
        repo = ProductRepository(db)
        
        items, total = await repo.get_filtered(
            tenant_id=tenant_id,
            search=search,
            category_id=category_id,
            supplier_id=supplier_id,
            is_active=is_active,
            low_stock=low_stock,
            pagination=pagination
        )
        
        metadata = create_pagination_metadata(pagination.page, pagination.page_size, total)
        return PaginatedResponse(items=items, metadata=metadata)
    except Exception as e:
        logger.error(f"Error en list_products: {str(e)}", exc_info=True)
        raise e


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    current_user: User = Depends(require_permission("products:create")),
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo producto (Solo Admins/Managers)"""
    repo = ProductRepository(db)
    tenant_id = current_user.tenant_id
    
    # Verificar si el SKU ya existe
    existing = await repo.get_by_sku(product_in.sku, tenant_id)
    if existing:
        raise DuplicateResourceException("Producto", "SKU", product_in.sku)
    
    # Verificar barcode si se proporciona
    if product_in.barcode:
        existing_barcode = await repo.get_by_barcode(product_in.barcode, tenant_id)
        if existing_barcode:
            raise DuplicateResourceException("Producto", "código de barras", product_in.barcode)
    
    # Crear producto
    product_dict = product_in.model_dump()
    product_dict["tenant_id"] = tenant_id
    product_dict["is_active"] = True if product_in.is_active else False
    
    product = await repo.create(product_dict, user_id=current_user.id)
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
    product_in: ProductUpdate,
    current_user: User = Depends(require_permission("products:edit")),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza un producto (Solo Admins/Managers)"""
    repo = ProductRepository(db)
    tenant_id = current_user.tenant_id
    
    # Verificar que el producto existe
    product = await repo.get_by_id(product_id, tenant_id)
    if not product:
        raise ProductNotFoundException(product_id)
    
    # Verificar SKU único si se está actualizando
    if product_in.sku and product_in.sku != product.sku:
        existing_sku = await repo.get_by_sku(product_in.sku, tenant_id)
        if existing_sku and existing_sku.id != product_id:
            raise DuplicateResourceException("Producto", "SKU", product_in.sku)

    # Verificar barcode único si se está actualizando
    if product_in.barcode and product_in.barcode != product.barcode:
        existing_barcode = await repo.get_by_barcode(product_in.barcode, tenant_id)
        if existing_barcode and existing_barcode.id != product_id:
            raise DuplicateResourceException("Producto", "código de barras", product_in.barcode)
    
    # Actualizar
    update_dict = product_in.model_dump(exclude_unset=True)
    updated_product = await repo.update(product_id, update_dict, tenant_id, user_id=current_user.id)
    await db.commit()
    await db.refresh(updated_product)
    
    logger.info(f"Producto actualizado: {product_id}")
    return updated_product


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_product(
    id: int,
    current_user: User = Depends(require_permission("products:delete")),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    """Elimina un producto (lógica de borrado suave)"""
    repo = ProductRepository(db)
    await repo.delete(id, tenant_id, user_id=current_user.id)
    await db.commit()
    return {"detail": "Producto eliminado"}


@router.get("/{product_id}/label")
async def get_product_label(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    """Genera un PDF con etiquetas para un producto específico"""
    repo = ProductRepository(db)
    product = await repo.get_by_id(product_id, tenant_id)
    if not product:
        raise ProductNotFoundException(product_id)
        
    pdf_buffer = LabelGenerator.generate_pdf([product], labels_per_row=2, rows_per_page=4)
    filename = f"etiqueta_{product.sku}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@router.get("/labels/bulk")
async def get_bulk_labels(
    ids: str = Query(..., description="IDs de productos separados por comas"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    """Genera un PDF con etiquetas para múltiples productos"""
    try:
        product_ids = [int(id_str) for id_str in ids.split(",") if id_str.strip()]
        repo = ProductRepository(db)
        products = []
        for pid in product_ids:
            p = await repo.get_by_id(pid, tenant_id)
            if p:
                products.append(p)
                
        if not products:
            raise HTTPException(status_code=404, detail="No se encontraron productos")
            
        pdf_buffer = LabelGenerator.generate_pdf(products)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=etiquetas_productos.pdf",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        logger.error(f"Error en etiquetas masivas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al generar las etiquetas")


@router.post("/import-csv", response_model=BulkImportResponse)
async def import_products_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("products:create")),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    if not file.filename.endswith('.csv'):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Solo se permiten archivos CSV")
    
    try:
        content = await file.read()
        decoded = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        
        repo = ProductRepository(db)
        created = 0
        skipped = 0
        errors = []
        
        for row in reader:
            try:
                # Mapeo de campos (soporta español e inglés)
                sku = row.get("sku")
                if not sku:
                    skipped += 1
                    errors.append("Fila omitida: Falta SKU")
                    continue
                    
                name = row.get("nombre") or row.get("name")
                if not name:
                    skipped += 1
                    errors.append(f"SKU {sku}: Falta nombre")
                    continue

                price_str = row.get("precio") or row.get("price") or "0"
                cost_str = row.get("costo") or row.get("cost")
                stock_str = row.get("stock") or "0"
                
                product_in = {
                    "name": name,
                    "sku": sku,
                    "price": Decimal(price_str.replace(',', '.')),
                    "cost": Decimal(cost_str.replace(',', '.')) if cost_str else None,
                    "stock": int(stock_str),
                    "barcode": row.get("codigo_barras") or row.get("barcode"),
                    "description": row.get("descripcion") or row.get("description"),
                    "min_stock": int(row.get("min_stock") or 10),
                }
                
                # Verificar duplicados
                existing = await repo.get_by_sku(sku, tenant_id)
                if existing:
                    skipped += 1
                    errors.append(f"SKU {sku} ya existe")
                    continue
                    
                await repo.create(product_in, tenant_id, user_id=current_user.id)
                created += 1
            except Exception as e:
                skipped += 1
                errors.append(f"Error procesando SKU {row.get('sku', 'unknown')}: {str(e)}")
                
        await db.commit()
        return BulkImportResponse(created=created, skipped=skipped, errors=errors)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")


@router.get("/low-stock/list", response_model=List[ProductOut])
async def get_low_stock_products(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene productos con stock bajo"""
    repo = ProductRepository(db)
    products = await repo.get_low_stock_products(tenant_id)
    return products


@router.post("/bulk", response_model=BulkImportResponse)
async def bulk_create_products(
    import_data: BulkProductImport,
    current_user: User = Depends(require_permission("products:create")),
    db: AsyncSession = Depends(get_db)
):
    """Importación masiva de productos (Solo Admins/Managers)"""
    repo = ProductRepository(db)
    tenant_id = current_user.tenant_id
    created_count = 0
    skipped_count = 0
    errors = []
    
    for product_data in import_data.products:
        try:
            # Verificar si el SKU ya existe
            existing = await repo.get_by_sku(product_data.sku, tenant_id)
            if existing:
                skipped_count += 1
                continue
            
            # Crear producto
            product_dict = product_data.model_dump()
            product_dict["tenant_id"] = tenant_id
            product_dict["is_active"] = True if product_data.is_active else False
            
            await repo.create(product_dict)
            created_count += 1
            
        except Exception as e:
            errors.append(f"Error en SKU {product_data.sku}: {str(e)}")
            continue
            
    await db.commit()
    
    return BulkImportResponse(
        created=created_count,
        skipped=skipped_count,
        errors=errors
    )


@router.get("/{product_id}/labels")
async def get_product_labels(
    product_id: int,
    quantity: int = Query(12, ge=1, le=100),
    current_user: User = Depends(require_permission("products:labels")),
    db: AsyncSession = Depends(get_db)
):
    """Genera etiquetas PDF para un producto específico"""
    repo = ProductRepository(db)
    tenant_id = current_user.tenant_id
    product = await repo.get_by_id(product_id, tenant_id)
    
    if not product:
        raise ProductNotFoundException(product_id)
    
    # Create a list with the same product repeated 'quantity' times
    products_list = [product for _ in range(quantity)]
    
    pdf_buffer = LabelGenerator.generate_pdf(products_list)
    
    filename = f"Etiquetas_{product.sku}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/labels/bulk")
async def get_bulk_labels(
    ids: str = Query(..., description="IDs de productos separados por comas"),
    current_user: User = Depends(require_permission("products:labels")),
    db: AsyncSession = Depends(get_db)
):
    """Genera etiquetas PDF para múltiples productos"""
    try:
        product_ids = [int(id_str) for id_str in ids.split(",")]
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="IDs inválidos")
        
    repo = ProductRepository(db)
    products = []
    for pid in product_ids:
        p = await repo.get_by_id(pid, current_user.tenant_id)
        if p:
            products.append(p)
            
    if not products:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No se encontraron productos")
        
    pdf_buffer = LabelGenerator.generate_pdf(products)
    
    filename = f"Etiquetas_Masivas_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )