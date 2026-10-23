from app.domain.shared.errors import ConflictError, DomainError, NotFoundError


class DuplicateProductError(ConflictError):
    def __init__(self, field: str, value: str):
        super().__init__(f"Producto con {field}='{value}' ya existe")


class ProductConflictError(ConflictError):
    def __init__(self):
        super().__init__("El producto choca con un registro existente (SKU o código de barras)")


class ProductRowError(DomainError):
    """Fila de importación inválida."""


class CategoryNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Categoría no encontrada")


class SupplierNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Proveedor no encontrado")


class ImportTooLargeError(DomainError):
    def __init__(self, limit: int):
        super().__init__(f"La importación supera el máximo de {limit} filas")


class DuplicateCodeError(ConflictError):
    """El código ya existe en el tenant (categoría o proveedor)."""


class CategoryParentNotFoundError(NotFoundError):
    def __init__(self, parent_id: int):
        super().__init__(f"Categoría padre con ID {parent_id} no encontrada")


class CategoryHierarchyError(DomainError):
    """La jerarquía propuesta es inválida (la categoría sería su propio ancestro)."""


class CategoryHasChildrenError(DomainError):
    def __init__(self, count: int):
        super().__init__(f"No se puede eliminar la categoría porque tiene {count} subcategorías")


class ProductBatchNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Lote no encontrado")


class BranchHasStockError(DomainError):
    def __init__(self, units: int):
        super().__init__(f"No se puede eliminar la sucursal: aún tiene {units} unidades en stock")
