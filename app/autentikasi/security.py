# app/autentikasi/security.py
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
import os
import json
import logging

# --- Tambahan Import ---
from sqlalchemy.orm import Session # Untuk tipe hint sesi database
from app.core.database import get_db # Untuk mendapatkan sesi database
from app.users.models import User # Import model User Anda
# --- Akhir Tambahan Import ---

logger = logging.getLogger(__name__)

# Inisialisasi Firebase Admin SDK (pastikan ini di awal file dan hanya berjalan sekali)
if not firebase_admin._apps:
    try:
        if os.path.exists(settings.FIREBASE_SERVICE_ACCOUNT_KEY):
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_KEY)
        elif settings.FIREBASE_SERVICE_ACCOUNT_KEY.strip().startswith('{'):
            cred = credentials.Certificate(json.loads(settings.FIREBASE_SERVICE_ACCOUNT_KEY))
        else:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY must be a valid file path or JSON string.")

        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing Firebase Admin SDK: {e}", exc_info=True)
        raise RuntimeError(f"Failed to initialize Firebase Admin SDK: {e}")

reusable_oauth2 = HTTPBearer(scheme_name="Authorization")

async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Security(reusable_oauth2)):
    logger.debug("Attempting to verify Firebase token...")

    if not firebase_admin._apps:
        logger.error("Firebase Admin SDK is not initialized when verify_firebase_token is called.")
        raise HTTPException(status_code=500, detail="Firebase Admin SDK not initialized.")

    token = credentials.credentials
    logger.debug(f"Received token (first 10 chars): {token[:10]}...") 

    try:
        decoded_token = auth.verify_id_token(token, clock_skew_seconds=5) 

        uid = decoded_token.get('uid')
        logger.info(f"Firebase token verified successfully for UID: {uid}")
        logger.debug(f"Decoded token payload: {decoded_token}")
        return decoded_token
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

# ---
## Fungsi get_current_active_user yang diperbarui

async def get_current_active_user(
    token_data: dict = Security(verify_firebase_token),
    db: Session = Depends(get_db) # Tambahkan dependensi sesi database
) -> User: # Menentukan tipe kembalian adalah objek User
    """
    Mengambil objek pengguna aktif dari database berdasarkan token Firebase yang diverifikasi.
    
    Args:
        token_data: Dict yang berisi payload token Firebase yang sudah diverifikasi.
        db: Sesi database SQLAlchemy, disuntikkan oleh FastAPI Depends.

    Returns:
        Objek User lengkap dari database.

    Raises:
        HTTPException: Jika UID tidak ditemukan di token, atau pengguna tidak ditemukan di database.
    """
    user_uid = token_data.get('uid')
    if not user_uid:
        logger.error("UID not found in Firebase token payload.")
        raise HTTPException(status_code=400, detail="UID not found in token.")
    
    # Mengambil objek User lengkap dari database
    user_in_db = db.query(User).filter(User.uid == user_uid).first()
    
    if not user_in_db:
        logger.warning(f"User with UID {user_uid} not found in database after Firebase verification.")
        raise HTTPException(status_code=404, detail="User not found in local database.")
    
    # Mengembalikan objek User lengkap
    return user_in_db

# Fungsi ini bisa Anda tambahkan jika ingin memverifikasi admin secara eksplisit
async def get_admin_user_token(current_user_token: dict = Security(verify_firebase_token)):
    # Asumsi: Anda memiliki 'admin' custom claim di token Firebase user admin
    # Atau Anda punya sistem role_id di database lokal yang bisa dicek
    # Untuk contoh ini, kita asumsikan ada custom claim 'admin': True
    if not current_user_token.get("admin", False):
        raise HTTPException(status_code=403, detail="Tidak memiliki hak akses admin.")
    return current_user_token