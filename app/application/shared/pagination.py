from typing import Generic, List, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 500


class PaginationParams(BaseModel):
    """Parámetros de paginación"""
    page: int = Field(default=1, ge=1, description="Número de página (inicia en 1)")
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"Tamaño de página (máximo {MAX_PAGE_SIZE})"
    )
    
    @property
    def offset(self) -> int:
        """Calcula el offset para la consulta"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Retorna el límite para la consulta"""
        return self.page_size


class PageMetadata(BaseModel):
    """Metadata de paginación"""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada genérica"""
    items: List[T]
    metadata: PageMetadata


def create_pagination_metadata(
    page: int,
    page_size: int,
    total_items: int
) -> PageMetadata:
    """
    Crea metadata de paginación
    
    Args:
        page: Número de página actual
        page_size: Tamaño de página
        total_items: Total de items
    
    Returns:
        PageMetadata con información de paginación
    """
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
    
    return PageMetadata(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )
