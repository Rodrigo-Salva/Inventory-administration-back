from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.defaults import DEFAULT_BRANCH_NAME, DEFAULT_EXPENSE_CATEGORIES
from app.infrastructure.persistence.models import Tenant, User
from app.infrastructure.persistence.models.inventory.branch import Branch
from app.infrastructure.persistence.models.purchasing.expense import ExpenseCategory
from app.domain.identity.entities import Identity, RegisteredTenantOwner
from app.infrastructure.persistence.repositories import UserRepository


class SqlAlchemyIdentityRepository:
    """Adaptador SQLAlchemy del puerto de identidad."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = UserRepository(db)

    async def find_by_email(self, email: str) -> Identity | None:
        user = await self.users.get_by_email(email)
        return self._to_domain(user) if user else None

    async def create_tenant_owner(
        self, email: str, password_hash: str
    ) -> RegisteredTenantOwner:
        try:
            tenant = Tenant(name=f"Tenant-{email.split('@')[0]}")
            self.db.add(tenant)
            await self.db.flush()
            # todo negocio nace con su sucursal principal y sus categorías de gasto (el stock vive por sucursal)
            branch = Branch(tenant_id=tenant.id, name=DEFAULT_BRANCH_NAME, is_active=True)
            self.db.add(branch)
            for name, description in DEFAULT_EXPENSE_CATEGORIES:
                self.db.add(ExpenseCategory(tenant_id=tenant.id, name=name, description=description))
            await self.db.flush()
            user = User(
                email=email,
                hashed_password=password_hash,
                tenant_id=tenant.id,
                branch_id=branch.id,
                is_admin=True,
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return RegisteredTenantOwner(user_id=user.id, tenant_id=tenant.id)
        except Exception:
            await self.db.rollback()
            raise

    @staticmethod
    def _to_domain(user: User) -> Identity:
        return Identity(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            password_hash=user.hashed_password,
            is_active=user.is_active,
        )
