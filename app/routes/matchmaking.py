from fastapi import APIRouter
from app import schemas, auth, models

router = APIRouter(prefix="/matchmaking", tags=["mečmejking"])

# Rute za mečmejking
