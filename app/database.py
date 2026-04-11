import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# Uzmi URL iz okruženja, ako ne postoji koristi SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chess.db")

# Ako je PostgreSQL, prilagodi za asyncpg (zameni postgresql:// sa postgresql+asyncpg://)
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
Base = declarative_base()
