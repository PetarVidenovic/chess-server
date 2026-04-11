from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, auth, models
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/tournaments", tags=["turniri"])
@router.post("/tournaments", response_model=schemas.TournamentOut)
async def create_tournament(t: schemas.TournamentCreate, current_user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # ... kreiranje turnira
    pass
