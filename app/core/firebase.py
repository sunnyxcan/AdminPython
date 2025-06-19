# app/core/firebase_admin.py
import firebase_admin
from firebase_admin import credentials, auth
import os
import json # Tambahkan import ini untuk memproses JSON
import base64 # Tambahkan import ini untuk mendekode Base64
import logging

logger = logging.getLogger(__name__)

# Nama variabel lingkungan tempat Anda menyimpan string Base64 kredensial
# Ganti dengan nama yang Anda gunakan di Netlify (misalnya FIREBASE_SERVICE_ACCOUNT_BASE64)
FIREBASE_CREDENTIALS_ENV_VAR = "FIREBASE_SERVICE_ACCOUNT_BASE64" # Sesuaikan nama ini

def initialize_firebase_admin():
    if not firebase_admin._apps: # Cek apakah Firebase Admin sudah diinisialisasi
        try:
            # Ambil string Base64 dari variabel lingkungan
            firebase_credentials_base64 = os.getenv(FIREBASE_CREDENTIALS_ENV_VAR)

            if firebase_credentials_base64:
                try:
                    # Dekode string Base64 kembali ke JSON byte
                    decoded_bytes = base64.b64decode(firebase_credentials_base64)
                    
                    # Dekode byte ke string UTF-8 dan kemudian parse sebagai JSON
                    service_account_info = json.loads(decoded_bytes.decode('utf-8'))

                    # Inisialisasi Firebase menggunakan objek Python dari JSON
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
    """Mengembalikan instance Firebase Auth."""
    if not firebase_admin._apps:
        initialize_firebase_admin() # Pastikan terinisialisasi sebelum digunakan
    return auth