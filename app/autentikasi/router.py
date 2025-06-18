# app/autentikasi/router.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging # Import logging

# Import dari Firebase
from firebase_admin import auth 
from app.core.firebase import get_firebase_auth # Ini perlu ada

from app.core.database import get_db
from app.users import schemas as user_schemas
from app.users import crud as user_crud
from app.users import models as user_models 
from app.roles import crud as role_crud
from app.autentikasi import security as auth_security

logger = logging.getLogger(__name__) # Inisialisasi logger di sini

router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"],
)

def get_firebase_auth_instance():
    """Dependency untuk mendapatkan instance Firebase Auth."""
    return get_firebase_auth()

@router.post("/register_user/", response_model=user_schemas.UserInDB, status_code=status.HTTP_201_CREATED)
async def register_user_from_firebase_signup(user_data: user_schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Mendaftarkan pengguna baru ke database lokal setelah pendaftaran Firebase berhasil.
    Asumsi: user_data.uid adalah UID dari Firebase.
    """
    # Periksa apakah pengguna dengan UID ini sudah ada di DB lokal
    db_user_by_uid = user_crud.get_user(db, user_data.uid)
    if db_user_by_uid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pengguna dengan UID ini sudah terdaftar di database lokal.")

    # Periksa apakah pengguna dengan email ini sudah terdaftar di DB lokal
    db_user_by_email = user_crud.get_user_by_email(db, user_data.email)
    if db_user_by_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pengguna dengan email ini sudah terdaftar di database lokal.")

    # Verifikasi role_id
    role = role_crud.get_role(db, role_id=user_data.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID peran tidak valid diberikan.")

    # Buat pengguna baru di database lokal
    new_user = user_crud.create_user(db=db, user=user_data)
    if not new_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gagal mendaftarkan pengguna di database lokal.")
    
    return new_user

@router.post("/login/", response_model=user_schemas.UserInDB)
async def login(
    current_user: user_models.User = Depends(auth_security.get_current_active_user)
):
    """
    Endpoint untuk login. Memverifikasi token Firebase dan mengembalikan data pengguna lokal.
    """
    return current_user

@router.get("/verify-auth/", response_model=user_schemas.UserInDB)
async def verify_auth_status(
    current_user: user_models.User = Depends(auth_security.get_current_active_user)
):
    """
    Memverifikasi status autentikasi pengguna saat ini dan mengembalikan data pengguna lokal.
    """
    return current_user

@router.post("/admin/create_user/", response_model=user_schemas.UserInDB, status_code=status.HTTP_201_CREATED) # Mengubah path dan response_model
async def create_new_user_by_admin(
    user_data: user_schemas.UserCreateByAdmin, # Menggunakan skema dari app.users.schemas
    db: Session = Depends(get_db),
    firebase_auth = Depends(get_firebase_auth_instance)
    # Anda mungkin ingin menambahkan otorisasi admin di sini
    # current_admin_user: user_models.User = Depends(auth_security.get_current_active_admin_user)
):
    """
    Membuat pengguna baru di Firebase Authentication dan database backend.
    Endpoint ini ditujukan untuk digunakan oleh admin.
    """
    db_user_by_email_local = user_crud.get_user_by_email(db, email=user_data.email)
    if db_user_by_email_local:
        raise HTTPException(status_code=400, detail="Email ini sudah terdaftar di database lokal.")

    db_role = role_crud.get_role(db, role_id=user_data.role_id)
    if not db_role:
        raise HTTPException(status_code=400, detail="Invalid role_id provided")

    new_uid = None
    try:
        firebase_user_record = auth.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.fullname,
            email_verified=False,
            disabled=False
        )
        new_uid = firebase_user_record.uid
        logger.info(f"Pengguna Firebase baru dibuat: {new_uid}")

    except auth.EmailAlreadyExistsError:
        logger.warning(f"Percobaan membuat pengguna dengan email yang sudah ada di Firebase: {user_data.email}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ini sudah terdaftar di Firebase.")
    except Exception as e:
        logger.error(f"Gagal membuat akun Firebase: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gagal membuat akun Firebase: {e}")

    try:
        # Perhatikan bahwa UserCreate membutuhkan 'uid' yang sudah diisi
        user_create_data = user_schemas.UserCreate( # Menggunakan skema dari app.users.schemas
            uid=new_uid,
            email=user_data.email,
            imageUrl=user_data.imageUrl,
            fullname=user_data.fullname,
            nickname=user_data.nickname,
            gender=user_data.gender,
            jabatan=user_data.jabatan,
            joinDate=user_data.joinDate,
            grupDate=user_data.grupDate,
            role_id=user_data.role_id,
            status=user_data.status,
            tanggalAkhirCuti=user_data.tanggalAkhirCuti
        )
        created_user_in_db = user_crud.create_user(db=db, user=user_create_data)
        logger.info(f"Pengguna berhasil disimpan ke database lokal: {created_user_in_db.uid}")
        return created_user_in_db

    except Exception as e:
        logger.error(f"Gagal menyimpan data pengguna ke database lokal setelah membuat di Firebase: {e}", exc_info=True)
        if new_uid:
            try:
                auth.delete_user(new_uid)
                logger.warning(f"User {new_uid} dihapus dari Firebase Auth karena gagal disimpan ke DB lokal.")
            except Exception as delete_e:
                logger.error(f"Gagal menghapus user {new_uid} dari Firebase Auth setelah error DB lokal: {delete_e}")
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan data pengguna ke database lokal: {e}")