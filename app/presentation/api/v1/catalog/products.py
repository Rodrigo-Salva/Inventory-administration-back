import csv
import io
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.catalog.dto import (
    CreateProductCommand,
    DeleteProductCommand,
    ImportProductsCommand,
    UpdateProductCommand,
)
from app.application.catalog.use_cases import CreateProduct, DeleteProduct, ImportProducts, UpdateProduct
from app.application.shared.pagination import PaginatedResponse, PaginationParams, create_pagination_metadata
from app.domain.inventory.errors import ProductNotFoundError
from app.infrastructure.config import settings
from app.infrastructure.external.label_generator import LabelGenerator
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User
from app.infrastructure.persistence.repositories.catalog.product_repo import ProductRepository
from app.presentation.api.v1.catalog.deps import (
    get_create_product,
    get_delete_product,
    get_import_products,
    get_update_product,
)
from app.presentation.dependencies import get_current_tenant, require_permission
from app.presentation.schemas.catalog.product import (
    BulkImportResponse,
    BulkProductImport,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    ProductWithRelations,
)

router = APIRouter()

MAX_LABEL_IDS = 200
PDF_HEADERS = {"Access-Control-Expose-Headers": "Content-Disposition"}


def _pdf(buffer, filename: str) -> StreamingResponse:
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}", **PDF_HEADERS},
    )


async def _product_or_404(db: AsyncSession, product_id: int, tenant_id: int):
    product = await ProductRepository(db).get_by_id(product_id, tenant_id)
    if not product:
        raise ProductNotFoundError(product_id)
    return product


@router.get("", response_model=PaginatedResponse[ProductWithRelations])
async def list_products(
    pagination: PaginationParams = Depends(),
    search: str = Query(None, description="Buscar por nombre, SKU o código de barras"),
    category_id: int = Query(None, description="Filtrar por categoría"),
    supplier_id: int = Query(None, description="Filtrar por proveedor"),
    is_active: bool = Query(None, description="Filtrar por estado activo"),
    low_stock: bool = Query(False, description="Solo productos con stock bajo"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Lista productos con paginación y filtros combinados"""
    items, total = await ProductRepository(db).get_filtered(
        tenant_id=tenant_id, search=search, category_id=category_id, supplier_id=supplier_id,
        is_active=is_active, low_stock=low_stock, pagination=pagination,
    )
    metadata = create_pagination_metadata(pagination.page, pagination.page_size, total)
    return PaginatedResponse(items=items, metadata=metadata)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    current_user: User = Depends(require_permission("products:create")),
    use_case: CreateProduct = Depends(get_create_product),
    db: AsyncSession = Depends(get_db),
):
    """Crea un nuevo producto"""
    product_id = await use_case.execute(
        CreateProductCommand(current_user.tenant_id, current_user.id, product_in.model_dump())
    )
    return await _product_or_404(db, product_id, current_user.tenant_id)


@router.get("/low-stock/list", response_model=List[ProductOut])
async def get_low_stock_products(
    tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)
):
    """Obtiene productos con stock bajo"""
    return await ProductRepository(db).get_low_stock_products(tenant_id)


@router.get("/labels/bulk")
async def get_bulk_labels(
    ids: str = Query(..., description="IDs de productos separados por comas"),
    current_user: User = Depends(require_permission("products:labels")),
    db: AsyncSession = Depends(get_db),
):
    """Genera etiquetas PDF para múltiples productos"""
    try:
        product_ids = [int(i) for i in ids.split(",") if i.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="IDs inválidos")
    if not product_ids or len(product_ids) > MAX_LABEL_IDS:
        raise HTTPException(status_code=400, detail=f"Indique entre 1 y {MAX_LABEL_IDS} productos")

    repo = ProductRepository(db)
    products = [p for p in [await repo.get_by_id(i, current_user.tenant_id) for i in product_ids] if p]
    if not products:
        raise HTTPException(status_code=404, detail="No se encontraron productos")
    return _pdf(LabelGenerator.generate_pdf(products), f"Etiquetas_Masivas_{datetime.now():%Y%m%d}.pdf")


@router.post("/import-csv", response_model=BulkImportResponse)
async def import_products_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("products:create")),
    use_case: ImportProducts = Depends(get_import_products),
):
    """Importa productos desde un CSV (columnas en español o inglés)"""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos CSV")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"El archivo supera {settings.max_upload_size_mb} MB")
    try:
        rows = tuple(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    except (UnicodeDecodeError, csv.Error):
        raise HTTPException(status_code=400, detail="El archivo no es un CSV UTF-8 válido")

    result = await use_case.from_csv_rows(ImportProductsCommand(current_user.tenant_id, current_user.id, rows))
    return BulkImportResponse(created=result.created, skipped=result.skipped, errors=result.errors)


@router.post("/bulk", response_model=BulkImportResponse)
async def bulk_create_products(
    import_data: BulkProductImport,
    current_user: User = Depends(require_permission("products:create")),
    use_case: ImportProducts = Depends(get_import_products),
):
    """Importación masiva de productos"""
    rows = tuple(p.model_dump() for p in import_data.products)
    result = await use_case.from_attributes(ImportProductsCommand(current_user.tenant_id, current_user.id, rows))
    return BulkImportResponse(created=result.created, skipped=result.skipped, errors=result.errors)


@router.get("/{product_id}", response_model=ProductWithRelations)
async def get_product(
    product_id: int, tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)
):
    """Obtiene un producto por ID"""
    return await _product_or_404(db, product_id, tenant_id)


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    product_in: ProductUpdate,
    current_user: User = Depends(require_permission("products:edit")),
    use_case: UpdateProduct = Depends(get_update_product),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza un producto"""
    await use_case.execute(
        UpdateProductCommand(
            current_user.tenant_id, current_user.id, product_id, product_in.model_dump(exclude_unset=True)
        )
    )
    return await _product_or_404(db, product_id, current_user.tenant_id)


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_product(
    id: int,
    current_user: User = Depends(require_permission("products:delete")),
    use_case: DeleteProduct = Depends(get_delete_product),
):
    """Elimina un producto (borrado lógico)"""
    await use_case.execute(DeleteProductCommand(current_user.tenant_id, current_user.id, id))
    return {"detail": "Producto eliminado"}


@router.get("/{product_id}/label")
async def get_product_label(
    product_id: int,
    current_user: User = Depends(require_permission("products:labels")),
    db: AsyncSession = Depends(get_db),
):
    """PDF con una hoja de etiquetas de un producto (2 por fila, 4 filas)"""
    product = await _product_or_404(db, product_id, current_user.tenant_id)
    return _pdf(LabelGenerator.generate_pdf([product], labels_per_row=2, rows_per_page=4), f"etiqueta_{product.sku}.pdf")


@router.get("/{product_id}/labels")
async def get_product_labels(
    product_id: int,
    quantity: int = Query(12, ge=1, le=100),
    current_user: User = Depends(require_permission("products:labels")),
    db: AsyncSession = Depends(get_db),
):
    """Genera `quantity` etiquetas PDF de un producto"""
    product = await _product_or_404(db, product_id, current_user.tenant_id)
    filename = f"Etiquetas_{product.sku}_{datetime.now():%Y%m%d}.pdf"
    return _pdf(LabelGenerator.generate_pdf([product] * quantity), filename)
