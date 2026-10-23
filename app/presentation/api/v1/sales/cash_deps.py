"""Composition root de caja, abonos y lealtad."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.cash_use_cases import (
    AdjustLoyaltyPoints,
    CloseCashSession,
    OpenCashSession,
    RegisterCreditPayment,
    UpdateLoyaltyConfig,
)
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.sales.cash_gateway import (
    SqlAlchemyCashSessions,
    SqlAlchemyCreditPayments,
    SqlAlchemyLoyaltyAdmin,
)
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def get_open_cash_session(db: AsyncSession = Depends(get_db)) -> OpenCashSession:
    return OpenCashSession(SqlAlchemyCashSessions(db), SqlAlchemyUnitOfWork(db))


def get_close_cash_session(db: AsyncSession = Depends(get_db)) -> CloseCashSession:
    return CloseCashSession(SqlAlchemyCashSessions(db), SqlAlchemyUnitOfWork(db))


def get_register_credit_payment(db: AsyncSession = Depends(get_db)) -> RegisterCreditPayment:
    return RegisterCreditPayment(SqlAlchemyCreditPayments(db), SqlAlchemyUnitOfWork(db))


def get_update_loyalty_config(db: AsyncSession = Depends(get_db)) -> UpdateLoyaltyConfig:
    return UpdateLoyaltyConfig(SqlAlchemyLoyaltyAdmin(db), SqlAlchemyUnitOfWork(db))


def get_adjust_loyalty_points(db: AsyncSession = Depends(get_db)) -> AdjustLoyaltyPoints:
    return AdjustLoyaltyPoints(SqlAlchemyLoyaltyAdmin(db), SqlAlchemyUnitOfWork(db))
