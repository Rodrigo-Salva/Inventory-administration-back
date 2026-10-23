from typing import Any, Callable

from app.application.catalog.dto import (
    CreateProductCommand,
    DeleteProductCommand,
    ImportProductsCommand,
    ImportResult,
    UpdateProductCommand,
)
from app.application.catalog.ports import ProductStore
from app.application.shared.ports import TenantResources, UnitOfWork
from app.domain.catalog import rules
from app.domain.catalog.errors import (
    CategoryNotFoundError,
    DuplicateProductError,
    ImportTooLargeError,
    SupplierNotFoundError,
)
from app.domain.inventory.errors import ProductNotFoundError
from app.domain.shared.errors import DomainError


class _CatalogUseCase:
    def __init__(self, products: ProductStore, resources: TenantResources, uow: UnitOfWork):
        self.products = products
        self.resources = resources
        self.uow = uow

    async def _check_unique(self, tenant_id: int, attrs: dict[str, Any], exclude_id: int | None = None):
        sku = attrs.get("sku")
        if sku:
            existing = await self.products.find_by_sku(tenant_id, sku)
            if existing and existing.id != exclude_id:
                raise DuplicateProductError("SKU", sku)
        barcode = attrs.get("barcode")
        if barcode:
            existing = await self.products.find_by_barcode(tenant_id, barcode)
            if existing and existing.id != exclude_id:
                raise DuplicateProductError("código de barras", barcode)

    async def _check_relations(self, tenant_id: int, attrs: dict[str, Any]):
        category_id, supplier_id = attrs.get("category_id"), attrs.get("supplier_id")
        if category_id and not await self.resources.category_exists(tenant_id, category_id):
            raise CategoryNotFoundError()
        if supplier_id and not await self.resources.supplier_exists(tenant_id, supplier_id):
            raise SupplierNotFoundError()

    async def _create(self, tenant_id: int, user_id: int, attrs: dict[str, Any]) -> int:
        await self._check_unique(tenant_id, attrs)
        await self._check_relations(tenant_id, attrs)
        return await self.products.create(tenant_id, user_id, {**attrs, "tenant_id": tenant_id})


class CreateProduct(_CatalogUseCase):
    async def execute(self, cmd: CreateProductCommand) -> int:
        try:
            product_id = await self._create(cmd.tenant_id, cmd.user_id, cmd.attributes)
            await self.uow.commit()
            return product_id
        except Exception:
            await self.uow.rollback()
            raise


class UpdateProduct(_CatalogUseCase):
    async def execute(self, cmd: UpdateProductCommand) -> int:
        try:
            if not await self.products.get(cmd.tenant_id, cmd.product_id):
                raise ProductNotFoundError(cmd.product_id)
            await self._check_unique(cmd.tenant_id, cmd.attributes, exclude_id=cmd.product_id)
            await self._check_relations(cmd.tenant_id, cmd.attributes)
            await self.products.update(cmd.tenant_id, cmd.user_id, cmd.product_id, cmd.attributes)
            await self.uow.commit()
            return cmd.product_id
        except Exception:
            await self.uow.rollback()
            raise


class DeleteProduct:
    def __init__(self, products: ProductStore, uow: UnitOfWork):
        self.products = products
        self.uow = uow

    async def execute(self, cmd: DeleteProductCommand) -> None:
        try:
            if not await self.products.soft_delete(cmd.tenant_id, cmd.user_id, cmd.product_id):
                raise ProductNotFoundError(cmd.product_id)
            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            raise


class ImportProducts(_CatalogUseCase):
    """Importa filas aisladas por savepoint: una fila inválida no afecta a las demás."""

    async def from_attributes(self, cmd: ImportProductsCommand) -> ImportResult:
        """Alta masiva JSON: los SKU repetidos se omiten en silencio."""
        return await self._run(cmd, parse=lambda row: row, report_duplicates=False)

    async def from_csv_rows(self, cmd: ImportProductsCommand) -> ImportResult:
        return await self._run(cmd, parse=rules.parse_csv_row, report_duplicates=True)

    async def _run(
        self, cmd: ImportProductsCommand, parse: Callable[[Any], dict], report_duplicates: bool
    ) -> ImportResult:
        if len(cmd.rows) > rules.MAX_IMPORT_ROWS:
            raise ImportTooLargeError(rules.MAX_IMPORT_ROWS)
        result = ImportResult()
        try:
            for row in cmd.rows:
                label = row.get("sku") or "desconocido"
                try:
                    attrs = parse(row)
                    await self._create(cmd.tenant_id, cmd.user_id, attrs)
                    result.created += 1
                except DuplicateProductError:
                    result.skipped += 1
                    if report_duplicates:
                        result.errors.append(f"SKU {label} ya existe")
                except DomainError as error:
                    result.skipped += 1
                    text = str(error)
                    result.errors.append(text if text.startswith(("SKU", "Fila")) else f"SKU {label}: {text}")
            await self.uow.commit()
            return result
        except Exception:
            await self.uow.rollback()
            raise
