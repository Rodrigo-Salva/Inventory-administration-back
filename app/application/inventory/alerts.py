"""Alertas de stock: crea, notifica y resuelve alertas según el nivel de inventario."""

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from app.application.shared.ports import TaskScheduler
from app.domain.inventory import rules

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StockLevel:
    product_id: int
    name: str
    stock: int
    min_stock: int


@dataclass(frozen=True)
class ActiveAlert:
    id: int
    alert_type: str


class AlertStore(Protocol):
    async def active_alerts(self, tenant_id: int, product_id: int) -> list[ActiveAlert]: ...

    async def open_alert(
        self, tenant_id: int, product_id: int, alert_type: str, stock: int, threshold: int, message: str
    ) -> None: ...

    async def resolve(self, alert_id: int) -> None: ...


class TenantContacts(Protocol):
    async def alert_email(self, tenant_id: int) -> str | None: ...


class AlertNotifier(Protocol):
    def stock_alert_email(self, product_name: str, stock: int, threshold: int) -> tuple[str, str]:
        """Devuelve (asunto, cuerpo) del correo de alerta."""
        ...

    async def send_email(self, to_email: str, subject: str, body: str) -> Any: ...


class StockAlerts:
    def __init__(self, store: AlertStore, contacts: TenantContacts, notifier: AlertNotifier):
        self.store = store
        self.contacts = contacts
        self.notifier = notifier

    async def check(self, level: StockLevel, tenant_id: int, scheduler: TaskScheduler | None = None) -> None:
        """Abre la alerta que corresponda (si no existe ya) y avisa por correo en segundo plano."""
        alert_type = rules.stock_alert_type(level.stock, level.min_stock)
        if alert_type is None:
            return
        active = await self.store.active_alerts(tenant_id, level.product_id)
        if any(a.alert_type == alert_type for a in active):
            return

        await self.store.open_alert(
            tenant_id, level.product_id, alert_type, level.stock,
            rules.alert_threshold(alert_type, level.min_stock),
            rules.alert_message(alert_type, level.name, level.stock, level.min_stock),
        )
        if scheduler is None:
            return
        email = await self.contacts.alert_email(tenant_id)
        if email:
            subject, body = self.notifier.stock_alert_email(
                level.name, level.stock, level.min_stock if level.stock > 0 else 0
            )
            scheduler.add_task(self.notifier.send_email, email, subject, body)
            logger.info("Notificación de stock encolada para %s", email)

    async def resolve_if_recovered(self, level: StockLevel, tenant_id: int) -> None:
        for alert in await self.store.active_alerts(tenant_id, level.product_id):
            if rules.alert_is_resolved(alert.alert_type, level.stock, level.min_stock):
                await self.store.resolve(alert.id)
