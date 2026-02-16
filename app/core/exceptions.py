from typing import Any, Optional
from fastapi import HTTPException, status


class InventoryBaseException(HTTPException):
    """Excepción base para el sistema de inventario"""
    
    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detail: str = "Error en el sistema de inventario",
        headers: Optional[dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class ResourceNotFoundException(InventoryBaseException):
    """Recurso no encontrado"""
    
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} con identificador '{identifier}' no encontrado"
        )


class ProductNotFoundException(ResourceNotFoundException):
    """Producto no encontrado"""
    
    def __init__(self, product_id: int):
        super().__init__("Producto", product_id)


class CategoryNotFoundException(ResourceNotFoundException):
    """Categoría no encontrada"""
    
    def __init__(self, category_id: int):
        super().__init__("Categoría", category_id)


class SupplierNotFoundException(ResourceNotFoundException):
    """Proveedor no encontrado"""
    
    def __init__(self, supplier_id: int):
        super().__init__("Proveedor", supplier_id)


class InsufficientStockException(InventoryBaseException):
    """Stock insuficiente para la operación"""
    
    def __init__(self, product_name: str, requested: int, available: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock insuficiente para '{product_name}'. Solicitado: {requested}, Disponible: {available}"
        )


class InvalidStockOperationException(InventoryBaseException):
    """Operación de stock inválida"""
    
    def __init__(self, reason: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operación de stock inválida: {reason}"
        )


class DuplicateResourceException(InventoryBaseException):
    """Recurso duplicado"""
    
    def __init__(self, resource: str, field: str, value: Any):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} con {field}='{value}' ya existe"
        )


class TenantMismatchException(InventoryBaseException):
    """El recurso no pertenece al tenant actual"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para acceder a este recurso"
        )


class ValidationException(InventoryBaseException):
    """Error de validación de datos"""
    
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message
        )


class BusinessRuleException(InventoryBaseException):
    """Violación de regla de negocio"""
    
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Regla de negocio violada: {message}"
        )
