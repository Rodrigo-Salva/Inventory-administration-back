from typing import Awaitable, Callable, TypeVar

from app.application.catalog.admin_dto import (
    CreateBatchCommand,
    CreateEntityCommand,
    DeleteEntityCommand,
    UpdateEntityCommand,
)
from app.application.catalog.admin_ports import BatchStore, BranchStore, CategoryStore, SupplierStore
from app.application.inventory.ports import BranchLedger
from app.application.shared.ports import BranchResolver, TenantResources, UnitOfWork
from app.domain.catalog.errors import (
    BranchHasStockError,
    CategoryHasChildrenError,
    CategoryHierarchyError,
    CategoryNotFoundError,
    CategoryParentNotFoundError,
    DuplicateCodeError,
    SupplierNotFoundError,
)
from app.domain.inventory.errors import BranchNotFoundError, ProductNotFoundError

T = TypeVar("T")


class _Transactional:
    uow: UnitOfWork

    async def _run(self, action: Callable[[], Awaitable[T]]) -> T:
        try:
            result = await action()
            await self.uow.commit()
            return result
        except Exception:
            await self.uow.rollback()
            raise


# ----------------------------------------------------------------- categorías
class _CategoryUseCase(_Transactional):
    def __init__(self, categories: CategoryStore, uow: UnitOfWork):
        self.categories = categories
        self.uow = uow

    async def _check_code(self, tenant_id: int, code: str | None, exclude_id: int | None = None):
        if code:
            existing = await self.categories.find_by_code(tenant_id, code)
            if existing and existing.id != exclude_id:
                raise DuplicateCodeError(f"Ya existe una categoría con el código '{code}'")

    async def _check_parent(self, tenant_id: int, parent_id: int | None, category_id: int | None = None):
        if not parent_id:
            return
        if not await self.categories.get(tenant_id, parent_id):
            raise CategoryParentNotFoundError(parent_id)
        # recorrer hacia arriba: si aparece la propia categoría, el cambio crearía un ciclo
        visited, current = set(), parent_id
        while current is not None and current not in visited:
            if current == category_id:
                raise CategoryHierarchyError("La jerarquía propuesta crearía un ciclo de categorías")
            visited.add(current)
            current = await self.categories.parent_of(tenant_id, current)


class CreateCategory(_CategoryUseCase):
    async def execute(self, cmd: CreateEntityCommand) -> int:
        async def action():
            await self._check_code(cmd.tenant_id, cmd.attributes.get("code"))
            await self._check_parent(cmd.tenant_id, cmd.attributes.get("parent_id"))
            return await self.categories.create(cmd.tenant_id, cmd.attributes)

        return await self._run(action)


class UpdateCategory(_CategoryUseCase):
    async def execute(self, cmd: UpdateEntityCommand) -> int:
        async def action():
            category = await self.categories.get(cmd.tenant_id, cmd.entity_id)
            if not category:
                raise CategoryNotFoundError()
            if cmd.changes.get("parent_id") == cmd.entity_id:
                raise CategoryHierarchyError("Una categoría no puede ser su propio padre")
            code = cmd.changes.get("code")
            if code and code != category.code:
                await self._check_code(cmd.tenant_id, code, exclude_id=category.id)
            await self._check_parent(cmd.tenant_id, cmd.changes.get("parent_id"), category.id)
            await self.categories.update(cmd.tenant_id, category.id, cmd.changes)
            return category.id

        return await self._run(action)


class DeleteCategory(_CategoryUseCase):
    async def execute(self, cmd: DeleteEntityCommand) -> None:
        async def action():
            if not await self.categories.get(cmd.tenant_id, cmd.entity_id):
                raise CategoryNotFoundError()
            children = await self.categories.children_count(cmd.tenant_id, cmd.entity_id)
            if children:
                raise CategoryHasChildrenError(children)
            await self.categories.soft_delete(cmd.tenant_id, cmd.entity_id)

        await self._run(action)


# ---------------------------------------------------------------- proveedores
class _SupplierUseCase(_Transactional):
    def __init__(self, suppliers: SupplierStore, uow: UnitOfWork):
        self.suppliers = suppliers
        self.uow = uow

    async def _check_code(self, tenant_id: int, code: str | None, exclude_id: int | None = None):
        if code:
            existing = await self.suppliers.find_by_code(tenant_id, code)
            if existing and existing.id != exclude_id:
                raise DuplicateCodeError(f"Proveedor con code='{code}' ya existe")


class CreateSupplier(_SupplierUseCase):
    async def execute(self, cmd: CreateEntityCommand) -> int:
        async def action():
            await self._check_code(cmd.tenant_id, cmd.attributes.get("code"))
            return await self.suppliers.create(cmd.tenant_id, cmd.attributes)

        return await self._run(action)


class UpdateSupplier(_SupplierUseCase):
    async def execute(self, cmd: UpdateEntityCommand) -> int:
        async def action():
            supplier = await self.suppliers.get(cmd.tenant_id, cmd.entity_id)
            if not supplier:
                raise SupplierNotFoundError()
            code = cmd.changes.get("code")
            if code and code != supplier.code:
                await self._check_code(cmd.tenant_id, code, exclude_id=supplier.id)
            await self.suppliers.update(cmd.tenant_id, supplier.id, cmd.changes)
            return supplier.id

        return await self._run(action)


class ToggleSupplierActive(_SupplierUseCase):
    async def execute(self, cmd: DeleteEntityCommand) -> int:
        async def action():
            supplier = await self.suppliers.get(cmd.tenant_id, cmd.entity_id)
            if not supplier:
                raise SupplierNotFoundError()
            await self.suppliers.update(cmd.tenant_id, supplier.id, {"is_active": not supplier.is_active})
            return supplier.id

        return await self._run(action)


class DeleteSupplier(_SupplierUseCase):
    async def execute(self, cmd: DeleteEntityCommand) -> None:
        async def action():
            if not await self.suppliers.get(cmd.tenant_id, cmd.entity_id):
                raise SupplierNotFoundError()
            await self.suppliers.soft_delete(cmd.tenant_id, cmd.entity_id)

        await self._run(action)


# ---------------------------------------------------------------- sucursales
class _BranchUseCase(_Transactional):
    def __init__(self, branches: BranchStore, uow: UnitOfWork):
        self.branches = branches
        self.uow = uow


class CreateBranch(_BranchUseCase):
    async def execute(self, cmd: CreateEntityCommand) -> int:
        return await self._run(lambda: self.branches.create(cmd.tenant_id, cmd.user_id, cmd.attributes))


class UpdateBranch(_BranchUseCase):
    async def execute(self, cmd: UpdateEntityCommand) -> int:
        async def action():
            if not await self.branches.get(cmd.tenant_id, cmd.entity_id):
                raise BranchNotFoundError()
            await self.branches.update(cmd.tenant_id, cmd.user_id, cmd.entity_id, cmd.changes)
            return cmd.entity_id

        return await self._run(action)


class DeleteBranch(_BranchUseCase):
    async def execute(self, cmd: DeleteEntityCommand) -> None:
        async def action():
            branch = await self.branches.get(cmd.tenant_id, cmd.entity_id)
            if not branch:
                raise BranchNotFoundError()
            if branch.stock_units > 0:
                raise BranchHasStockError(branch.stock_units)
            await self.branches.soft_delete(cmd.tenant_id, cmd.user_id, cmd.entity_id)

        await self._run(action)


# --------------------------------------------------------------------- lotes
class CreateBatch(_Transactional):
    def __init__(
        self,
        batches: BatchStore,
        resources: TenantResources,
        uow: UnitOfWork,
        ledger: BranchLedger | None = None,
        branches: BranchResolver | None = None,
    ):
        self.batches = batches
        self.resources = resources
        self.uow = uow
        self.ledger = ledger
        self.branches = branches

    async def execute(self, cmd: CreateBatchCommand) -> int:
        async def action():
            if await self.resources.missing_products(cmd.tenant_id, {cmd.product_id}):
                raise ProductNotFoundError(cmd.product_id)
            batch_id = await self.batches.create(
                cmd.tenant_id, cmd.product_id, cmd.batch_number, cmd.expiration_date,
                cmd.initial_quantity, cmd.is_active,
            )
            if self.ledger and self.branches and cmd.initial_quantity > 0:
                # el lote ingresa stock: entra a una sucursal (el total del producto es la suma de sucursales)
                branch_id = await self.branches.resolve(cmd.tenant_id, cmd.user_id, cmd.branch_id)
                await self.ledger.open_position(cmd.tenant_id, cmd.product_id, branch_id)
                await self.ledger.post(
                    cmd.tenant_id, cmd.user_id, cmd.product_id, branch_id, cmd.initial_quantity, "entry",
                    reference=f"LOTE {cmd.batch_number}", notes="Ingreso de lote", batch_id=batch_id,
                )
            return batch_id

        return await self._run(action)
