# app/users/router.py

# --- IMPOR YANG DIBUTUHKAN ---
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.users import schemas, crud, models
from app.roles.crud import get_role # Untuk memvalidasi role_id
from app.roles.models import Role 
from app.autentikasi.security import verify_firebase_token
from app.core.firebase import firebase_admin # Import instance firebase_admin yang sudah diinisialisasi
import logging 

# Inisialisasi logger untuk router ini
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- INISIALISASI ROUTER ---
router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
    
)

# --- DEKORATOR DAN FUNGSI on_event ---
@router.on_event("startup")
async def create_users_table():
    from app.core.database import engine, Base
    Base.metadata.create_all(bind=engine)
    print("Tabel 'users' dipastikan ada atau dibuat.")

# --- SEMUA ENDPOINT ANDA BERADA DI SINI ---

@router.post("/", response_model=schemas.UserInDB, status_code=status.HTTP_201_CREATED)
def create_new_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="User with this email already registered")

    role = get_role(db, role_id=user.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role_id")

    return crud.create_user(db=db, user=user)

@router.get("/", response_model=List[schemas.UserInDB])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_uid}", response_model=schemas.UserInDB)
def read_user(user_uid: str, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_uid=user_uid)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/{user_uid}", response_model=schemas.UserInDB)
def update_existing_user(
    user_uid: str, 
    user: schemas.UserUpdate, 
    db: Session = Depends(get_db),
    # Tambahkan dependensi autentikasi di sini
    current_user_token: dict = Depends(verify_firebase_token) 
):
    # Opsional: Jika Anda ingin memastikan UID dari token cocok dengan UID di path
    # user_uid_from_token = current_user_token.get('uid')
    # if user_uid_from_token != user_uid:
    #     raise HTTPException(status_code=403, detail="UID in token does not match user_uid in path.")

    if user.email:
        existing_user_with_email = crud.get_user_by_email(db, email=user.email)
        if existing_user_with_email and str(existing_user_with_email.uid) != user_uid:
            raise HTTPException(status_code=400, detail="Email already taken by another user")

    if user.role_id:
        role = get_role(db, role_id=user.role_id)
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role_id")

    db_user = crud.update_user(db, user_uid=user_uid, user_update=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found or invalid role_id")
    return db_user

# --- FUNGSI DELETE YANG DIMODIFIKASI ---
@router.delete("/{user_uid}", status_code=status.HTTP_200_OK)
def delete_existing_user(user_uid: str, db: Session = Depends(get_db)):
    # LANGKAH 1: Hapus pengguna dari database lokal (PostgreSQL) terlebih dahulu
    logger.info(f"Mencoba menghapus pengguna dengan UID '{user_uid}' dari database lokal.")
    is_deleted = crud.delete_user(db, user_uid=user_uid)
    
    if not is_deleted:
        raise HTTPException(status_code=404, detail="User not found in local database or failed to delete.")
    
    logger.info(f"Pengguna dengan UID '{user_uid}' berhasil dihapus dari database lokal.")

    # LANGKAH 2: Sekarang, coba hapus pengguna dari firebase Auth
    try:
        logger.info(f"Mencoba menghapus pengguna dengan UID '{user_uid}' dari firebase Auth.")
        # Panggil firebase_admin yang kini diimpor dari core.firebase
        firebase_admin.auth.delete_user(user_uid) # <--- PERBAIKAN DI SINI! Hapus '.admin'
        logger.info(f"Pengguna dengan UID '{user_uid}' berhasil dihapus dari firebase Auth.")

    except Exception as e:
        if "User not found" in str(e) or "Cannot delete user" in str(e):
            logger.warning(
                f"Peringatan: Pengguna dengan UID '{user_uid}' telah dihapus dari database lokal, "
                f"tetapi tidak ditemukan atau gagal dihapus dari firebase Auth. Ini mungkin "
                f"menyebabkan inkonsistensi. Error: {e}"
            )
        else:
            logger.error(
                f"Kesalahan fatal saat menghapus pengguna dari firebase Auth (UID: {user_uid}) "
                f"setelah berhasil dihapus dari database lokal. Error: {e}. "
                f"Pengguna mungkin masih ada di firebase Auth. Cek log backend untuk detail."
            )

    return {"message": "User deleted successfully from local database. firebase Auth deletion status logged."}