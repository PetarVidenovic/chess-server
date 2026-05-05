from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, auth, models
from app.database import get_db
from app.auth import get_current_user
import os
import shutil

router = APIRouter(prefix="/users", tags=["korisnici"])

@router.get("/me", response_model=schemas.UserOut)
async def get_my_profile(current_user: models.User = Depends(get_current_user)):
    return current_user

# NOVA RUTA: upload profilne slike
@router.post("/me/profile_picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Kreiraj folder za slike ako ne postoji
    upload_dir = "static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Sanitizuj ime fajla
    ext = file.filename.split(".")[-1]
    filename = f"user_{current_user.id}_{current_user.username}.{ext}"
    file_path = os.path.join(upload_dir, filename)
    
    # Sačuvaj fajl
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Ažuriraj putanju u bazi (dodaj kolonu profile_picture u model User)
    current_user.profile_picture = f"/static/uploads/{filename}"
    await db.commit()
    return {"profile_picture": current_user.profile_picture
