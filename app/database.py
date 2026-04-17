import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chess.db")

if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
Base = declarative_base()

AsyncSessionLocal = SessionLocal

async def init_db():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # create_all proverava da li tabela već postoji pre nego što je kreira
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    
async def get_db():
    async with SessionLocal() as session:
        yield session
