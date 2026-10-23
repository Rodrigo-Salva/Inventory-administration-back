"""Composition root de identidad (usuarios y roles)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.identity.user_dto import Actor
from app.application.identity.user_use_cases import (
    CreateRole,
    CreateUser,
    DeleteRole,
    DeleteUser,
    UpdateOwnProfile,
    UpdateRole,
    UpdateUser,
)
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.identity.user import User
from app.infrastructure.persistence.repositories.identity.directories import (
    SqlAlchemyRoleDirectory,
    SqlAlchemyUserDirectory,
)
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.security.password_hasher import PasslibPasswordHasher


def actor_of(user: User) -> Actor:
    return Actor(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=str(getattr(user.role, "value", user.role)),
        is_admin=bool(user.is_admin),
    )


def _user_parts(db: AsyncSession):
    return SqlAlchemyUserDirectory(db), PasslibPasswordHasher(), SqlAlchemyUnitOfWork(db)


def get_create_user(db: AsyncSession = Depends(get_db)) -> CreateUser:
    return CreateUser(*_user_parts(db))


def get_update_user(db: AsyncSession = Depends(get_db)) -> UpdateUser:
    return UpdateUser(*_user_parts(db))


def get_update_own_profile(db: AsyncSession = Depends(get_db)) -> UpdateOwnProfile:
    return UpdateOwnProfile(*_user_parts(db))


def get_delete_user(db: AsyncSession = Depends(get_db)) -> DeleteUser:
    return DeleteUser(SqlAlchemyUserDirectory(db), SqlAlchemyUnitOfWork(db))


def get_create_role(db: AsyncSession = Depends(get_db)) -> CreateRole:
    return CreateRole(SqlAlchemyRoleDirectory(db), SqlAlchemyUnitOfWork(db))


def get_update_role(db: AsyncSession = Depends(get_db)) -> UpdateRole:
    return UpdateRole(SqlAlchemyRoleDirectory(db), SqlAlchemyUnitOfWork(db))


def get_delete_role(db: AsyncSession = Depends(get_db)) -> DeleteRole:
    return DeleteRole(SqlAlchemyRoleDirectory(db), SqlAlchemyUnitOfWork(db))
