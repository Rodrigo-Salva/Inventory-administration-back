from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.inventory.errors import BranchNotFoundError
from app.infrastructure.persistence.models.identity.user import User
from app.infrastructure.persistence.models.inventory.branch import Branch

MAIN_BRANCH_NAME = "Sucursal Principal"


class SqlAlchemyBranchResolver:
    """Adaptador SQLAlchemy del puerto BranchResolver.

    Orden de decisión: sucursal pedida (debe ser del tenant) -> sucursal del usuario ->
    sucursal principal del tenant (la llamada «Sucursal Principal» o, si no, la más antigua).
    Si el tenant no tiene ninguna, crea la principal para no bloquear la operación.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _active(self, tenant_id: int, branch_id: int) -> int | None:
        result = await self.db.execute(
            select(Branch.id).where(
                Branch.id == branch_id, Branch.tenant_id == tenant_id, Branch.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def _main(self, tenant_id: int) -> int:
        result = await self.db.execute(
            select(Branch.id)
            .where(Branch.tenant_id == tenant_id, Branch.is_deleted == False)  # noqa: E712
            .order_by((Branch.name == MAIN_BRANCH_NAME).desc(), Branch.id.asc())
            .limit(1)
        )
        branch_id = result.scalar_one_or_none()
        if branch_id is None:
            branch = Branch(tenant_id=tenant_id, name=MAIN_BRANCH_NAME, is_active=True)
            self.db.add(branch)
            await self.db.flush()
            branch_id = branch.id
        return branch_id

    async def resolve(self, tenant_id: int, user_id: int | None, requested_branch_id: int | None = None) -> int:
        if requested_branch_id is not None:
            if await self._active(tenant_id, requested_branch_id) is None:
                raise BranchNotFoundError()
            return requested_branch_id
        if user_id is not None:
            user_branch = (
                await self.db.execute(select(User.branch_id).where(User.id == user_id, User.tenant_id == tenant_id))
            ).scalar_one_or_none()
            if user_branch is not None and await self._active(tenant_id, user_branch) is not None:
                return user_branch
        return await self._main(tenant_id)
