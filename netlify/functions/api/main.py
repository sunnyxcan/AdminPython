# backend/netlify/functions/api/main.py

import os
import json
import base64
import logging
import sys

# Konfigurasi logging untuk fungsi ini.
# Ini akan membantu Anda melihat log di dasbor Netlify.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- PENTING: Penyesuaian PYTHONPATH ---
# Baris ini memastikan bahwa direktori 'backend' ditambahkan ke Python's import path.
# Ini memungkinkan import modul dari 'app' (misalnya app.main, app.core) berfungsi dengan benar
# ketika fungsi Netlify dijalankan dari dalam direktori 'api'.
# os.path.dirname(__file__) adalah 'backend/netlify/functions/api/'
# os.path.join(..., '../../') akan naik dua level ke 'backend/'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
logger.info(f"Added {sys.path[0]} to sys.path for module imports.")

# --- Inisialisasi Firebase ---
# Logika ini dipindahkan langsung ke dalam fungsi Netlify
# untuk memastikan Firebase diinisialisasi dengan benar di setiap eksekusi fungsi
# (terutama penting untuk cold starts).
import firebase_admin
from firebase_admin import credentials, auth

# Nama variabel lingkungan tempat Anda menyimpan string Base64 kredensial Firebase
FIREBASE_CREDENTIALS_ENV_VAR = "FIREBASE_SERVICE_ACCOUNT_BASE64" 

def initialize_firebase_admin_for_function():
    """
    Menginisialisasi Firebase Admin SDK jika belum diinisialisasi.
    Membaca kredensial dari variabel lingkungan Base64.
    """
    if not firebase_admin._apps: # Cek apakah Firebase Admin sudah diinisialisasi di konteks ini
        try:
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
                    logger.info("Firebase Admin SDK berhasil diinisialisasi dari variabel lingkungan untuk fungsi ini.")
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
            logger.critical(f"Kesalahan umum saat inisialisasi Firebase Admin SDK di fungsi: {e}")
            raise
    else:
        logger.info("Firebase Admin SDK sudah diinisialisasi untuk fungsi ini.")


# --- Impor Aplikasi FastAPI Utama ---
# Ini adalah inti dari adapter. Kita mengimpor instance 'app' FastAPI Anda
# dari file aslinya.
try:
    # Memastikan path import benar relatif terhadap sys.path yang kita atur.
    # Jika aplikasi FastAPI Anda berada di `backend/app/main.py`,
    # maka ini akan mengimpornya sebagai `app.main`.
    from app.main import app as fastapi_app
    logger.info("Aplikasi FastAPI (app.main:app) berhasil diimpor.")
except ImportError as e:
    logger.critical(f"Gagal mengimpor aplikasi FastAPI: {e}. Pastikan struktur proyek dan PYTHONPATH sudah benar.")
    # Jika gagal mengimpor, tidak ada gunanya melanjutkan.
    raise RuntimeError(f"FATAL: Tidak dapat mengimpor aplikasi FastAPI: {e}")

# --- Adapter untuk Netlify Functions ---
# Netlify Python Functions memerlukan handler bernama 'handler' yang menerima 'event' dan 'context'.
# Untuk aplikasi ASGI (seperti FastAPI), kita menggunakan `ServerlessFunction`
# yang disediakan oleh lingkungan Netlify untuk membungkusnya.
try:
    from netlify_integration import ServerlessFunction
    logger.info("`ServerlessFunction` dari `netlify_integration` berhasil diimpor.")
except ImportError:
    logger.warning("`netlify_integration.ServerlessFunction` tidak ditemukan di lingkungan lokal. Ini normal saat pengembangan, tapi pastikan deployment di Netlify.")
    # Jika Anda ingin menguji secara lokal tanpa Netlify CLI, Anda mungkin perlu menyediakan ServerlessFunction dummy.
    # Untuk tujuan deployment Netlify, ini akan disediakan.
    ServerlessFunction = None

# Titik masuk utama untuk fungsi Netlify.
def handler(event, context):
    """
    Handler utama untuk Netlify Function yang memproses event dan meneruskannya ke aplikasi FastAPI.
    """
    # Pastikan aplikasi FastAPI dan adapter Netlify tersedia.
    if not fastapi_app or not ServerlessFunction:
        logger.error("Konfigurasi server tidak lengkap: Aplikasi FastAPI atau ServerlessFunction tidak tersedia.")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Server configuration error: FastAPI app or Netlify handler missing."})
        }

    # Inisialisasi Firebase sebelum memproses setiap permintaan.
    # Ini memastikan bahwa setiap pemanggilan fungsi memiliki kredensial yang valid.
    try:
        initialize_firebase_admin_for_function()
    except Exception as e:
        logger.critical(f"Gagal inisialisasi Firebase sebelum menangani permintaan: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Server error: Firebase initialization failed. {str(e)}"})
        }

    # Membungkus aplikasi FastAPI dengan ServerlessFunction dan memproses event.
    # Ini akan meneruskan permintaan HTTP dari Netlify ke router FastAPI Anda.
    lambda_handler = ServerlessFunction(fastapi_app)
    return lambda_handler(event, context)