from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Parámetros de paginación"""
    page: int = Field(default=1, ge=1, description="Número de página (inicia en 1)")
    page_size: int = Field(
        default=settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description=f"Tamaño de página (máximo {settings.max_page_size})"
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


async def paginate(
    db: AsyncSession,
    query,
    pagination: PaginationParams,
    model_class: type = None
) -> tuple[List, int]:
    """
    Ejecuta una consulta paginada
    
    Args:
        db: Sesión de base de datos
        query: Query de SQLAlchemy
        pagination: Parámetros de paginación
        model_class: Clase del modelo (opcional, para contar)
    
    Returns:
        Tupla con (items, total_count)
    """
    # Obtener total de items
    if model_class:
        count_query = select(func.count()).select_from(model_class)
        # Copiar filtros del query original si existen
        if hasattr(query, 'whereclause') and query.whereclause is not None:
            count_query = count_query.where(query.whereclause)
    else:
        count_query = select(func.count()).select_from(query.subquery())
    
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0
    
    # Aplicar paginación
    paginated_query = query.offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(paginated_query)
    items = result.scalars().all()
    
    return items, total_count


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
