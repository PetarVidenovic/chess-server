from fastapi import APIRouter
from app import schemas, auth, models

router = APIRouter(prefix="/games", tags=["igre"])

# Rute za igre
