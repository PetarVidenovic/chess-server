# app/routes/leaderboard.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app import schemas, auth, models
from app.database import get_db

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

@router.get("/")
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.User).order_by(desc(models.User.wins)).limit(50)
    )
    users = result.scalars().all()
    return [
        {
            "username": u.username,
            "wins": u.wins,
            "losses": u.losses,
            "draws": u.draws,
            "rating": u.rating if hasattr(u, "rating") else 0
        }
        for u in users
    ]
