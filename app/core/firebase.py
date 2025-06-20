# app/core/firebase.py
import firebase_admin
from firebase_admin import credentials, auth
import os
import logging
import json
from app.core.config import settings # <-- Pastikan Anda mengimpor settings di sini

logger = logging.getLogger(__name__)

# Hapus baris ini:
# FIREBASE_SERVICE_ACCOUNT_KEY_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_JSON")

def initialize_firebase_admin():
    if not firebase_admin._apps:
        try:
            # Gunakan settings.FIREBASE_SERVICE_ACCOUNT_KEY
            if settings.FIREBASE_SERVICE_ACCOUNT_KEY: # Memastikan variabel tidak kosong
                # Sekarang, selalu asumsikan ini adalah string JSON
                cred_json = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_KEY)
                cred = credentials.Certificate(cred_json)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK berhasil diinisialisasi dari settings.FIREBASE_SERVICE_ACCOUNT_KEY.")
            else:
                logger.error("settings.FIREBASE_SERVICE_KEY tidak ditemukan atau kosong.")
                raise ValueError("Firebase Admin SDK JSON content not found in settings.")
        except json.JSONDecodeError as e:
            logger.critical(f"Gagal mengurai JSON Firebase Admin SDK dari settings: {e}")
            raise RuntimeError(f"Failed to initialize Firebase Admin SDK: JSON parsing error - {e}")
        except Exception as e:
            logger.critical(f"Gagal menginisialisasi Firebase Admin SDK: {e}")
            raise RuntimeError(f"Failed to initialize Firebase Admin SDK: {e}")
    else:
        logger.info("Firebase Admin SDK sudah diinisialisasi.")

def get_firebase_auth():
    """Mengembalikan instance Firebase Auth."""
    if not firebase_admin._apps:
        initialize_firebase_admin()
    return auth