"""Reglas puras de facturación de suscripciones."""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.billing.errors import PlanNotConfiguredError

SUBSCRIPTION_DAYS = 30
DEFAULT_PLAN = "premium"
TENANT_REFERENCE_PREFIX = "tenant_"


def resolve_price(
    plan: str, catalog_price: Decimal | None, client_price: Decimal | None, strict: bool
) -> Decimal:
    """El precio lo define el servidor; el del cliente solo se acepta si no es modo estricto."""
    if catalog_price is not None:
        return catalog_price
    if strict or client_price is None:
        raise PlanNotConfiguredError(plan)
    return client_price


def tenant_reference(tenant_id: int) -> str:
    return f"{TENANT_REFERENCE_PREFIX}{tenant_id}"


def parse_tenant_reference(reference: str | None) -> int | None:
    if not reference or not reference.startswith(TENANT_REFERENCE_PREFIX):
        return None
    suffix = reference[len(TENANT_REFERENCE_PREFIX):]
    return int(suffix) if suffix.isdigit() else None


def next_expiry(current: datetime | None, now: datetime | None = None) -> datetime:
    """Renueva 30 días desde hoy o desde el vencimiento vigente (lo que sea posterior)."""
    now = now or datetime.now(timezone.utc)
    if current is not None and current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    base = current if current and current > now else now
    return base + timedelta(days=SUBSCRIPTION_DAYS)


def valid_webhook_signature(secret: str, signature: str | None, request_id: str | None, data_id: str | None) -> bool:
    """Valida la cabecera x-signature de Mercado Pago (HMAC-SHA256 del manifest)."""
    if not (signature and data_id):
        return False
    parts = dict(p.strip().split("=", 1) for p in signature.split(",") if "=" in p)
    timestamp, received = parts.get("ts"), parts.get("v1")
    if not (timestamp and received):
        return False
    manifest = f"id:{data_id.lower()};request-id:{request_id or ''};ts:{timestamp};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)
