from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .. import schemas, auth, models
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=schemas.UserOut)
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    # provera email i username
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Email already exists")
    result = await db.execute(select(models.User).where(models.User.username == user.username))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Username already taken")

    hashed = auth.get_password_hash(user.password)
    db_user = models.User(email=user.email, username=user.username, hashed_password=hashed)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/login")
async def login(user: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    db_user = result.scalar_one_or_none()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    token = auth.create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer", "user_id": db_user.id}
