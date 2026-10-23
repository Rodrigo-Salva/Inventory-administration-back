from app.domain.shared.errors import DomainError


class PlanNotConfiguredError(DomainError):
    def __init__(self, plan: str):
        super().__init__(f"El plan '{plan}' no está configurado. Contacte al administrador del sistema.")


class PaymentGatewayError(DomainError):
    def __init__(self, detail: str):
        super().__init__(f"Mercado Pago Error: {detail}")
