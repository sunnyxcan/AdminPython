# app/core/firebase.py (Ini adalah file yang diimpor oleh app/main.py Anda)
import firebase_admin
from firebase_admin import credentials, auth
import os
import json
import base64
import logging

logger = logging.getLogger(__name__)

# Ini harus konsisten dengan nama variabel lingkungan di Netlify dan config.py
FIREBASE_CREDENTIALS_ENV_VAR = "FIREBASE_SERVICE_ACCOUNT_BASE64" 

def initialize_firebase_admin():
    if not firebase_admin._apps:
        try:
            firebase_credentials_base64 = os.getenv(FIREBASE_CREDENTIALS_ENV_VAR)

            if firebase_credentials_base64:
                try:
                    decoded_bytes = base64.b64decode(firebase_credentials_base64)
                    service_account_info = json.loads(decoded_bytes.decode('utf-8'))
                    cred = credentials.Certificate(service_account_info)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase Admin SDK berhasil diinisialisasi dari variabel lingkungan.")
                except (json.JSONDecodeError, base64.binascii.Error) as e:
                    logger.critical(f"Gagal mendekode atau mem-parsing kredensial Firebase dari variabel lingkungan: {e}")
                    raise ValueError("Format kredensial Firebase di variabel lingkungan tidak valid.")
                except Exception as e:
                    logger.critical(f"Gagal menginisialisasi Firebase Admin SDK dengan kredensial dari variabel lingkungan: {e}")
                    raise
            else:
                logger.error(f"Variabel lingkungan '{FIREBASE_CREDENTIALS_ENV_VAR}' tidak ditemukan. Firebase tidak diinisialisasi.")
                raise ValueError(f"Firebase Admin SDK kredensial tidak ditemukan di variabel lingkungan '{FIREBASE_CREDENTIALS_ENV_VAR}'")
        except Exception as e:
            logger.critical(f"Kesalahan umum saat inisialisasi Firebase Admin SDK: {e}")
            raise
    else:
        logger.info("Firebase Admin SDK sudah diinisialisasi.")

def get_firebase_auth():
    if not firebase_admin._apps:
        initialize_firebase_admin()
    return auth