from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, models
from ..database import get_db
from ..auth import get_current_user   # <-- This is the problematic line

router = APIRouter(prefix="/users", tags=["korisnici"])

@router.get("/me", response_model=schemas.UserOut)
async def get_my_profile(current_user: models.User = Depends(get_current_user)):
    return current_user
