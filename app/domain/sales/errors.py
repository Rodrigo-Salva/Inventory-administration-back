from app.domain.shared.errors import ConflictError, DomainError, ForbiddenError, NotFoundError


class SaleNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Venta no encontrada")


class SaleAlreadyAnnulledError(DomainError):
    def __init__(self):
        super().__init__("La venta ya ha sido anulada")


class InsufficientLoyaltyPointsError(DomainError):
    def __init__(self):
        super().__init__("El cliente no tiene puntos suficientes para redimir.")


class LoyaltyMinimumNotMetError(DomainError):
    def __init__(self, minimum: int):
        super().__init__(f"No se cumple el mínimo de puntos para redención ({minimum}).")


class CreditCustomerRequiredError(DomainError):
    def __init__(self):
        super().__init__("Debe seleccionar un cliente para ventas a crédito.")


class InsufficientCreditError(DomainError):
    def __init__(self):
        super().__init__("El cliente no tiene cupo de crédito suficiente.")


class CashSessionAlreadyOpenError(ConflictError):
    def __init__(self):
        super().__init__("Ya tienes una sesión de caja abierta.")


class NoOpenCashSessionError(NotFoundError):
    def __init__(self):
        super().__init__("No tienes una sesión de caja abierta.")


class InvalidCashAmountError(DomainError):
    def __init__(self):
        super().__init__("Los saldos de caja no pueden ser negativos.")


class CreditNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Crédito no encontrado.")


class CreditAlreadyPaidError(DomainError):
    def __init__(self):
        super().__init__("Este crédito ya está pagado.")


class InvalidPaymentError(DomainError):
    def __init__(self):
        super().__init__("El monto del abono debe ser mayor a 0.")


class PaymentExceedsBalanceError(DomainError):
    def __init__(self, amount, remaining):
        super().__init__(f"El monto del abono ({amount}) supera el saldo pendiente ({remaining}).")


class CustomerNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Cliente no encontrado.")


class InvalidLoyaltyConfigError(DomainError):
    """Parámetros de lealtad fuera de rango (descuentos negativos, divisores cero)."""


class InvalidLoyaltyAdjustmentError(DomainError):
    """Ajuste de puntos inválido (cero o dejaría al cliente en negativo)."""


class DuplicateCustomerError(ConflictError):
    def __init__(self, document_number: str):
        super().__init__(f"Cliente con document_number='{document_number}' ya existe")


class CreditManagementForbiddenError(ForbiddenError):
    def __init__(self):
        super().__init__("Se requiere el permiso 'credits:manage' para modificar el límite de crédito")


class InvalidCreditLimitError(DomainError):
    def __init__(self):
        super().__init__("El límite de crédito no puede ser negativo")


class QuoteNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Cotización no encontrada")


class QuoteNotConvertibleError(DomainError):
    """La cotización ya fue convertida o fue rechazada."""


class InvalidQuoteError(DomainError):
    """Cotización sin ítems o con referencias inválidas."""
