# app/core/firebase_admin.py
import firebase_admin
from firebase_admin import credentials, auth
import os
import logging

logger = logging.getLogger(__name__)

# Path ke serviceAccountKey.json Anda
# Pastikan ini aman dan tidak terekspos di repositori publik
# Anda bisa menyimpannya di luar proyek atau menggunakan variabel lingkungan
SERVICE_ACCOUNT_KEY_PATH = os.getenv("FIREBASE_ADMIN_SDK_PATH", "path/to/your/serviceAccountKey.json")

def initialize_firebase_admin():
    if not firebase_admin._apps: # Cek apakah Firebase Admin sudah diinisialisasi
        try:
            # Menggunakan variabel lingkungan untuk path jika tersedia, atau path langsung
            if os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
                cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK berhasil diinisialisasi.")
            else:
                logger.error(f"File service account key tidak ditemukan di: {SERVICE_ACCOUNT_KEY_PATH}")
                raise FileNotFoundError(f"Firebase Admin SDK key file not found at {SERVICE_ACCOUNT_KEY_PATH}")
        except Exception as e:
            logger.critical(f"Gagal menginisialisasi Firebase Admin SDK: {e}")
            raise
    else:
        logger.info("Firebase Admin SDK sudah diinisialisasi.")

def get_firebase_auth():
    """Mengembalikan instance Firebase Auth."""
    if not firebase_admin._apps:
        initialize_firebase_admin() # Pastikan terinisialisasi sebelum digunakan
    return auth