from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, auth, models
from app.database import get_db
from app.auth import get_current_user   # <-- This is the problematic line

router = APIRouter(prefix="/users", tags=["korisnici"])

@router.get("/me", response_model=schemas.UserOut)
async def get_my_profile(current_user: models.User = Depends(get_current_user)):
    return current_user
