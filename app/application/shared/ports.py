from typing import Any, Callable, Protocol


class TaskScheduler(Protocol):
    """Ejecuta trabajo diferido tras responder (p. ej. enviar un email)."""

    def add_task(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None: ...


class UnitOfWork(Protocol):
    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TenantResources(Protocol):
    """Verifica que los recursos referenciados pertenezcan al tenant."""

    async def missing_products(self, tenant_id: int, product_ids: set[int]) -> set[int]: ...

    async def branch_exists(self, tenant_id: int, branch_id: int) -> bool: ...

    async def supplier_exists(self, tenant_id: int, supplier_id: int) -> bool: ...

    async def category_exists(self, tenant_id: int, category_id: int) -> bool: ...

    async def customer_exists(self, tenant_id: int, customer_id: int) -> bool: ...


class BranchResolver(Protocol):
    """Decide en qué sucursal opera un movimiento de stock."""

    async def resolve(self, tenant_id: int, user_id: int | None, requested_branch_id: int | None = None) -> int:
        """Sucursal pedida (debe ser del tenant) -> sucursal del usuario -> sucursal principal."""
        ...
