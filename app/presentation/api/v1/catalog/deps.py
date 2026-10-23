"""Composition root del catálogo."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.catalog.use_cases import CreateProduct, DeleteProduct, ImportProducts, UpdateProduct
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.catalog.product_store import SqlAlchemyProductStore
from app.infrastructure.persistence.tenant_resources import SqlAlchemyTenantResources
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def _parts(db: AsyncSession):
    return SqlAlchemyProductStore(db), SqlAlchemyTenantResources(db), SqlAlchemyUnitOfWork(db)


def get_create_product(db: AsyncSession = Depends(get_db)) -> CreateProduct:
    return CreateProduct(*_parts(db))


def get_update_product(db: AsyncSession = Depends(get_db)) -> UpdateProduct:
    return UpdateProduct(*_parts(db))


def get_delete_product(db: AsyncSession = Depends(get_db)) -> DeleteProduct:
    store, _, uow = _parts(db)
    return DeleteProduct(store, uow)


def get_import_products(db: AsyncSession = Depends(get_db)) -> ImportProducts:
    return ImportProducts(*_parts(db))
