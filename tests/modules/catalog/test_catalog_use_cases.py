import pytest

from app.application.catalog.dto import (
    CreateProductCommand,
    DeleteProductCommand,
    ImportProductsCommand,
    ProductRef,
    UpdateProductCommand,
)
from app.application.catalog.use_cases import CreateProduct, DeleteProduct, ImportProducts, UpdateProduct
from app.domain.catalog import rules
from app.domain.catalog.errors import (
    CategoryNotFoundError,
    DuplicateProductError,
    ImportTooLargeError,
    ProductRowError,
    SupplierNotFoundError,
)
from app.domain.inventory.errors import ProductNotFoundError


class World:
    """Doble en memoria de ProductStore, TenantResources y UnitOfWork."""

    def __init__(self, existing=(), categories=(1,), suppliers=(1,)):
        self.products = {p.id: p for p in existing}
        self.categories, self.suppliers = set(categories), set(suppliers)
        self.created, self.updated, self.deleted = [], [], []
        self.next_id = 100
        self.commits = self.rollbacks = 0

    async def get(self, tenant_id, product_id):
        return self.products.get(product_id)

    async def find_by_sku(self, tenant_id, sku):
        return next((p for p in self.products.values() if p.sku == sku), None)

    async def find_by_barcode(self, tenant_id, barcode):
        return next((p for p in self.products.values() if p.barcode == barcode), None)

    async def create(self, tenant_id, user_id, attributes):
        self.next_id += 1
        self.products[self.next_id] = ProductRef(self.next_id, attributes["sku"], attributes.get("barcode"))
        self.created.append(attributes)
        return self.next_id

    async def update(self, tenant_id, user_id, product_id, attributes):
        self.updated.append((product_id, attributes))

    async def soft_delete(self, tenant_id, user_id, product_id):
        if product_id not in self.products:
            return False
        self.deleted.append(product_id)
        return True

    async def category_exists(self, tenant_id, category_id):
        return category_id in self.categories

    async def supplier_exists(self, tenant_id, supplier_id):
        return supplier_id in self.suppliers

    async def branch_exists(self, tenant_id, branch_id):
        return True

    async def missing_products(self, tenant_id, ids):
        return set()

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


EXISTING = ProductRef(1, "SKU-1", "BAR-1")


def test_parse_csv_row_supports_spanish_and_english_headers():
    row = {"sku": " A1 ", "nombre": "Cafe", "precio": "12,50", "costo": "8", "stock": "3", "barcode": "123"}
    parsed = rules.parse_csv_row(row)
    assert parsed["sku"] == "A1" and str(parsed["price"]) == "12.50" and parsed["stock"] == 3
    assert parsed["barcode"] == "123" and parsed["min_stock"] == 10


def test_parse_csv_row_rejects_bad_rows():
    for row in ({"nombre": "x"}, {"sku": "A"}, {"sku": "A", "name": "x", "price": "abc"},
                {"sku": "A", "name": "x", "price": "0"}, {"sku": "A", "name": "x", "price": "1", "stock": "-1"}):
        with pytest.raises(ProductRowError):
            rules.parse_csv_row(row)


async def test_create_product_checks_uniqueness_and_relations():
    w = World(existing=[EXISTING])
    uc = CreateProduct(w, w, w)
    with pytest.raises(DuplicateProductError) as err:
        await uc.execute(CreateProductCommand(1, 2, {"sku": "SKU-1"}))
    assert str(err.value) == "Producto con SKU='SKU-1' ya existe"
    with pytest.raises(DuplicateProductError):
        await uc.execute(CreateProductCommand(1, 2, {"sku": "NEW", "barcode": "BAR-1"}))
    with pytest.raises(CategoryNotFoundError):
        await uc.execute(CreateProductCommand(1, 2, {"sku": "NEW", "category_id": 9}))
    with pytest.raises(SupplierNotFoundError):
        await uc.execute(CreateProductCommand(1, 2, {"sku": "NEW", "supplier_id": 9}))
    assert not w.created and w.rollbacks == 4

    product_id = await uc.execute(CreateProductCommand(1, 2, {"sku": "NEW", "category_id": 1}))
    assert product_id == 101 and w.created[0]["tenant_id"] == 1 and w.commits == 1


async def test_update_product_allows_same_sku_but_not_someone_elses():
    other = ProductRef(2, "SKU-2", None)
    w = World(existing=[EXISTING, other])
    uc = UpdateProduct(w, w, w)
    await uc.execute(UpdateProductCommand(1, 2, 1, {"sku": "SKU-1", "name": "n"}))
    assert w.updated == [(1, {"sku": "SKU-1", "name": "n"})]
    with pytest.raises(DuplicateProductError):
        await uc.execute(UpdateProductCommand(1, 2, 1, {"sku": "SKU-2"}))
    with pytest.raises(ProductNotFoundError):
        await uc.execute(UpdateProductCommand(1, 2, 77, {"name": "x"}))


async def test_delete_product():
    w = World(existing=[EXISTING])
    await DeleteProduct(w, w).execute(DeleteProductCommand(1, 2, 1))
    assert w.deleted == [1]
    with pytest.raises(ProductNotFoundError):
        await DeleteProduct(w, w).execute(DeleteProductCommand(1, 2, 55))


async def test_csv_import_isolates_bad_rows_and_reports():
    w = World(existing=[EXISTING])
    rows = (
        {"sku": "OK-1", "name": "A", "price": "5"},
        {"sku": "SKU-1", "name": "dup", "price": "5"},
        {"name": "sin sku", "price": "5"},
        {"sku": "BAD", "name": "x", "price": "abc"},
        {"sku": "OK-2", "name": "B", "price": "7", "stock": "4"},
    )
    result = await ImportProducts(w, w, w).from_csv_rows(ImportProductsCommand(1, 2, rows))
    assert (result.created, result.skipped) == (2, 3)
    assert "SKU SKU-1 ya existe" in result.errors and "Fila omitida: Falta SKU" in result.errors
    assert any("BAD" in e for e in result.errors) and w.commits == 1


async def test_bulk_import_skips_duplicates_silently_and_limits_size():
    w = World(existing=[EXISTING])
    rows = ({"sku": "SKU-1", "name": "dup"}, {"sku": "N-1", "name": "ok", "category_id": 9},
            {"sku": "N-2", "name": "ok"})
    result = await ImportProducts(w, w, w).from_attributes(ImportProductsCommand(1, 2, rows))
    assert (result.created, result.skipped) == (1, 2)
    assert len(result.errors) == 1 and "Categoría no encontrada" in result.errors[0]

    big = tuple({"sku": f"S{i}", "name": "x"} for i in range(rules.MAX_IMPORT_ROWS + 1))
    with pytest.raises(ImportTooLargeError):
        await ImportProducts(w, w, w).from_attributes(ImportProductsCommand(1, 2, big))


async def test_batch_stock_enters_a_branch_through_the_ledger():
    from datetime import date

    from app.application.catalog.admin_dto import CreateBatchCommand
    from app.application.catalog.admin_use_cases import CreateBatch

    class Fake:
        def __init__(self):
            self.posts, self.commits = [], 0

        async def create(self, *args):
            return 4  # BatchStore.create

        async def missing_products(self, tenant_id, ids):
            return set()

        async def commit(self):
            self.commits += 1

        async def rollback(self):
            pass

        async def resolve(self, tenant_id, user_id, requested_branch_id=None):
            return requested_branch_id or 7

        async def open_position(self, *args, **kwargs):
            return object()

        async def post(self, tenant_id, user_id, product_id, branch_id, delta, movement_type, **kw):
            self.posts.append((branch_id, delta, movement_type, kw.get("batch_id")))
            return 1

    w = Fake()
    cmd = CreateBatchCommand(1, 5, "L-1", date(2030, 1, 1), 12, user_id=2)
    assert await CreateBatch(w, w, w, ledger=w, branches=w).execute(cmd) == 4
    assert w.posts == [(7, 12, "entry", 4)] and w.commits == 1

    w = Fake()  # lote sin cantidad inicial: no mueve stock
    await CreateBatch(w, w, w, ledger=w, branches=w).execute(CreateBatchCommand(1, 5, "L-2", date(2030, 1, 1), 0))
    assert w.posts == []
