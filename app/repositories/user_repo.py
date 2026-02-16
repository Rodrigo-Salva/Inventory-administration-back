from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models import User
from .base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repositorio para usuarios"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    async def get_by_email(self, email: str) -> User | None:
        """Obtiene un usuario por email"""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
