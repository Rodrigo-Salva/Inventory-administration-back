import asyncio
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.user import User

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:28demarzo@localhost:5432/inventory_saas")
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def restore():
    async with async_session() as session:
        # Buscar el usuario admin
        result = await session.execute(select(User).where(User.email == 'admin@demo.com'))
        user = result.scalars().first()
        
        if user:
            print(f"Restoring user: {user.email}")
            user.is_admin = True
            user.role = 'SUPERADMIN'
            user.is_active = True
            user.role_obj_id = None 
            
            await session.commit()
            print("Successfully restored admin to SUPERADMIN status.")
        else:
            print("User admin@demo.com not found.")
    await engine.dispose()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(restore())
    finally:
        loop.close()
