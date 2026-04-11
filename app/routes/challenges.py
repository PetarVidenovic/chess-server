from fastapi import APIRouter
from app import schemas, auth, models
from app.auth import get_current_user

router = APIRouter(prefix="/challenges", tags=["izazovi"])

# Rute za izazove
