"""Composition root de categorías, proveedores, sucursales y lotes."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.catalog import admin_use_cases as uc
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.catalog.admin_stores import (
    SqlAlchemyBatchStore,
    SqlAlchemyCategoryStore,
    SqlAlchemySupplierStore,
)
from app.infrastructure.persistence.repositories.inventory.branch_ledger import SqlAlchemyBranchLedger
from app.infrastructure.persistence.repositories.inventory.branch_resolver import SqlAlchemyBranchResolver
from app.infrastructure.persistence.repositories.inventory.branch_store import SqlAlchemyBranchStore
from app.infrastructure.persistence.tenant_resources import SqlAlchemyTenantResources
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def _uow(db: AsyncSession) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(db)


def get_create_category(db: AsyncSession = Depends(get_db)) -> uc.CreateCategory:
    return uc.CreateCategory(SqlAlchemyCategoryStore(db), _uow(db))


def get_update_category(db: AsyncSession = Depends(get_db)) -> uc.UpdateCategory:
    return uc.UpdateCategory(SqlAlchemyCategoryStore(db), _uow(db))


def get_delete_category(db: AsyncSession = Depends(get_db)) -> uc.DeleteCategory:
    return uc.DeleteCategory(SqlAlchemyCategoryStore(db), _uow(db))


def get_create_supplier(db: AsyncSession = Depends(get_db)) -> uc.CreateSupplier:
    return uc.CreateSupplier(SqlAlchemySupplierStore(db), _uow(db))


def get_update_supplier(db: AsyncSession = Depends(get_db)) -> uc.UpdateSupplier:
    return uc.UpdateSupplier(SqlAlchemySupplierStore(db), _uow(db))


def get_toggle_supplier(db: AsyncSession = Depends(get_db)) -> uc.ToggleSupplierActive:
    return uc.ToggleSupplierActive(SqlAlchemySupplierStore(db), _uow(db))


def get_delete_supplier(db: AsyncSession = Depends(get_db)) -> uc.DeleteSupplier:
    return uc.DeleteSupplier(SqlAlchemySupplierStore(db), _uow(db))


def get_create_branch(db: AsyncSession = Depends(get_db)) -> uc.CreateBranch:
    return uc.CreateBranch(SqlAlchemyBranchStore(db), _uow(db))


def get_update_branch(db: AsyncSession = Depends(get_db)) -> uc.UpdateBranch:
    return uc.UpdateBranch(SqlAlchemyBranchStore(db), _uow(db))


def get_delete_branch(db: AsyncSession = Depends(get_db)) -> uc.DeleteBranch:
    return uc.DeleteBranch(SqlAlchemyBranchStore(db), _uow(db))


def get_create_batch(db: AsyncSession = Depends(get_db)) -> uc.CreateBatch:
    return uc.CreateBatch(
        SqlAlchemyBatchStore(db), SqlAlchemyTenantResources(db), _uow(db),
        ledger=SqlAlchemyBranchLedger(db), branches=SqlAlchemyBranchResolver(db),
    )
