from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant, User
from app.modules.identity.domain.entities import Identity, RegisteredTenantOwner
from app.repositories import UserRepository


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
            user = User(
                email=email,
                hashed_password=password_hash,
                tenant_id=tenant.id,
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
