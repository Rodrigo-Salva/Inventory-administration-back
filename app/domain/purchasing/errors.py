from app.domain.shared.errors import DomainError, NotFoundError


class PurchaseNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Compra no encontrada")


class InvalidPurchaseError(DomainError):
    """La compra viola una regla (sin ítems, estado inválido)."""


class PurchaseNotReceivableError(DomainError):
    def __init__(self):
        super().__init__(
            "No se pudo recibir la compra. Verifique que exista y esté en estado Borrador."
        )
