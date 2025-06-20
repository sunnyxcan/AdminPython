# app/core/firebase.py
import firebase_admin
from firebase_admin import credentials, auth
import os
import logging
import json # Tambahkan ini

logger = logging.getLogger(__name__)

# Menggunakan variabel lingkungan untuk konten JSON, bukan path file
FIREBASE_SERVICE_ACCOUNT_KEY_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_JSON") # Nama variabel lingkungan baru

def initialize_firebase_admin():
    if not firebase_admin._apps:
        try:
            if FIREBASE_SERVICE_ACCOUNT_KEY_JSON:
                # Muat dari string JSON
                cred_json = json.loads(FIREBASE_SERVICE_ACCOUNT_KEY_JSON)
                cred = credentials.Certificate(cred_json)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK berhasil diinisialisasi dari variabel lingkungan JSON.")
            else:
                logger.error("Variabel lingkungan FIREBASE_SERVICE_ACCOUNT_KEY_JSON tidak ditemukan atau kosong.")
                raise ValueError("Firebase Admin SDK JSON content not found in environment variable.")
        except json.JSONDecodeError as e:
            logger.critical(f"Gagal mengurai JSON Firebase Admin SDK dari variabel lingkungan: {e}")
            raise
        except Exception as e:
            logger.critical(f"Gagal menginisialisasi Firebase Admin SDK: {e}")
            raise
    else:
        logger.info("Firebase Admin SDK sudah diinisialisasi.")

def get_firebase_auth():
    """Mengembalikan instance Firebase Auth."""
    if not firebase_admin._apps:
        initialize_firebase_admin()
    return auth