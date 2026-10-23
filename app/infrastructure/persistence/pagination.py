from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.shared.pagination import PaginationParams


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
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0
    
    # Aplicar paginación
    paginated_query = query.offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(paginated_query)
    items = result.scalars().all()
    
    return items, total_count
