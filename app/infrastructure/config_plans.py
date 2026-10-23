from decimal import Decimal

from app.infrastructure.config import settings


class SettingsPlanCatalog:
    """Catálogo de planes tomado de la configuración (SUBSCRIPTION_PLANS)."""

    def price_for(self, plan: str) -> Decimal | None:
        price = settings.subscription_plans.get(plan)
        return Decimal(str(price)) if price is not None else None

    @property
    def strict(self) -> bool:
        return settings.environment.lower() == "production"
