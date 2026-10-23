from app.domain.shared.errors import DomainError, NotFoundError


class ProductNotFoundError(NotFoundError):
    def __init__(self, product_id: int):
        super().__init__(f"Producto con identificador '{product_id}' no encontrado")


class BatchNotFoundError(DomainError):
    def __init__(self, batch_id: int):
        super().__init__(f"Lote ID {batch_id} no encontrado")


class InsufficientStockError(DomainError):
    def __init__(self, item_name: str, requested: int, available: int):
        super().__init__(
            f"Stock insuficiente para '{item_name}'. Solicitado: {requested}, Disponible: {available}"
        )


class InvalidAdjustmentError(DomainError):
    """Tipo o cantidad de ajuste inválidos."""


class InsufficientBranchStockError(DomainError):
    def __init__(self, product_id: int):
        super().__init__(f"Stock insuficiente en sucursal origen para el producto {product_id}")


class TransferNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Traslado no encontrado")


class InvalidTransferError(DomainError):
    """El traslado viola una regla (mismo origen y destino, sin ítems, estado inválido)."""


class BranchNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Sucursal no encontrada")


class InvalidStockOperationError(DomainError):
    """Cantidad o stock objetivo inválidos."""


class InvalidAuditError(DomainError):
    """La auditoría no existe, ya finalizó o el conteo es inválido."""
