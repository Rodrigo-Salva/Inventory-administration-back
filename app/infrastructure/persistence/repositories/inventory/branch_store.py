from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.catalog.admin_dto import BranchRef
from app.infrastructure.persistence.models.inventory.branch import Branch
from app.infrastructure.persistence.models.inventory.product_branch import ProductBranch
from app.infrastructure.persistence.repositories.inventory.branch_repo import BranchRepository


class SqlAlchemyBranchStore:
    """Adaptador SQLAlchemy del puerto BranchStore."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BranchRepository(db)

    async def get(self, tenant_id: int, branch_id: int) -> BranchRef | None:
        result = await self.db.execute(
            select(Branch.id).where(
                Branch.id == branch_id, Branch.tenant_id == tenant_id, Branch.is_deleted == False  # noqa: E712
            )
        )
        if result.scalar_one_or_none() is None:
            return None
        units = (
            await self.db.execute(
                select(func.coalesce(func.sum(ProductBranch.stock), 0)).where(ProductBranch.branch_id == branch_id)
            )
        ).scalar()
        return BranchRef(branch_id, int(units or 0))

    async def create(self, tenant_id: int, user_id: int | None, attributes: dict[str, Any]) -> int:
        branch = await self.repo.create({**attributes, "tenant_id": tenant_id}, user_id=user_id)
        return branch.id

    async def update(
        self, tenant_id: int, user_id: int | None, branch_id: int, changes: dict[str, Any]
    ) -> None:
        await self.repo.update(branch_id, changes, tenant_id, user_id=user_id)

    async def soft_delete(self, tenant_id: int, user_id: int | None, branch_id: int) -> None:
        await self.repo.delete(branch_id, tenant_id, user_id=user_id)
