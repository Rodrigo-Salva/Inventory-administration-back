from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.identity.user_dto import RoleSnapshot, UserSnapshot
from app.domain.identity.errors import EmailAlreadyRegisteredError, UserInUseError
from app.infrastructure.persistence.models.identity.role import Permission, Role
from app.infrastructure.persistence.models.identity.user import User, UserRole


def _value(enum_or_str) -> str:
    return str(getattr(enum_or_str, "value", enum_or_str))


class SqlAlchemyUserDirectory:
    """Adaptador SQLAlchemy del puerto UserDirectory."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def email_taken(self, email: str, exclude_user_id: int | None = None) -> bool:
        query = select(User.id).where(func.lower(User.email) == email.lower())
        if exclude_user_id is not None:
            query = query.where(User.id != exclude_user_id)
        return (await self.db.execute(query)).first() is not None

    async def get(self, tenant_id: int, user_id: int) -> UserSnapshot | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        return UserSnapshot(user.id, _value(user.role), bool(user.is_admin), bool(user.is_active))

    async def role_exists(self, tenant_id: int, role_id: int) -> bool:
        result = await self.db.execute(select(Role.id).where(Role.id == role_id, Role.tenant_id == tenant_id))
        return result.scalar_one_or_none() is not None

    async def create(self, tenant_id: int, attributes: dict[str, Any]) -> int:
        data = {**attributes, "tenant_id": tenant_id}
        if "role" in data:
            data["role"] = UserRole(_value(data["role"]))
        user = User(**data)
        try:
            async with self.db.begin_nested():
                self.db.add(user)
                await self.db.flush()
        except IntegrityError as error:
            raise EmailAlreadyRegisteredError() from error
        return user.id

    async def update(self, tenant_id: int, user_id: int, attributes: dict[str, Any]) -> None:
        user = (
            await self.db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
        ).scalar_one()
        try:
            async with self.db.begin_nested():
                for key, value in attributes.items():
                    setattr(user, key, UserRole(_value(value)) if key == "role" and value else value)
                await self.db.flush()
        except IntegrityError as error:
            raise EmailAlreadyRegisteredError() from error

    async def delete(self, tenant_id: int, user_id: int) -> None:
        user = (
            await self.db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
        ).scalar_one()
        try:
            async with self.db.begin_nested():
                await self.db.delete(user)
                await self.db.flush()
        except IntegrityError as error:
            raise UserInUseError() from error


class SqlAlchemyRoleDirectory:
    """Adaptador SQLAlchemy del puerto RoleDirectory."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def missing_permissions(self, permission_ids: set[int]) -> set[int]:
        result = await self.db.execute(select(Permission.id).where(Permission.id.in_(permission_ids)))
        return permission_ids - set(result.scalars().all())

    async def name_taken(self, tenant_id: int, name: str, exclude_role_id: int | None = None) -> bool:
        query = select(Role.id).where(Role.tenant_id == tenant_id, func.lower(Role.name) == name.lower())
        if exclude_role_id is not None:
            query = query.where(Role.id != exclude_role_id)
        return (await self.db.execute(query)).first() is not None

    async def get(self, tenant_id: int, role_id: int) -> RoleSnapshot | None:
        role = (
            await self.db.execute(select(Role.id).where(Role.id == role_id, Role.tenant_id == tenant_id))
        ).scalar_one_or_none()
        if role is None:
            return None
        users = (
            await self.db.execute(select(func.count(User.id)).where(User.role_id == role_id))
        ).scalar() or 0
        return RoleSnapshot(role_id, users)

    async def _permissions(self, permission_ids) -> list[Permission]:
        if not permission_ids:
            return []
        result = await self.db.execute(select(Permission).where(Permission.id.in_(permission_ids)))
        return list(result.scalars().all())

    async def create(
        self, tenant_id: int, name: str, description: str | None, permission_ids: tuple[int, ...]
    ) -> int:
        role = Role(tenant_id=tenant_id, name=name, description=description)
        role.permissions = await self._permissions(permission_ids)
        self.db.add(role)
        await self.db.flush()
        return role.id

    async def update(
        self, tenant_id: int, role_id: int, changes: dict[str, Any], permission_ids: tuple[int, ...] | None
    ) -> None:
        role = (
            await self.db.execute(
                select(Role)
                .options(selectinload(Role.permissions))
                .where(Role.id == role_id, Role.tenant_id == tenant_id)
            )
        ).scalar_one()
        for key, value in changes.items():
            setattr(role, key, value)
        if permission_ids is not None:
            role.permissions = await self._permissions(permission_ids)
        await self.db.flush()

    async def delete(self, tenant_id: int, role_id: int) -> None:
        role = (
            await self.db.execute(
                select(Role)
                .options(selectinload(Role.permissions))
                .where(Role.id == role_id, Role.tenant_id == tenant_id)
            )
        ).scalar_one()
        await self.db.delete(role)
        await self.db.flush()
