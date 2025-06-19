# api/index.py

import os
import sys

# Tambahkan direktori root proyek ke Python path
# Ini penting agar modul-modul dari folder 'app' dapat diimpor
# Misalnya, jika 'app' berada satu level di atas 'api'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app # Impor aplikasi FastAPI Anda dari app/main.py
from app.core.firebase import initialize_firebase_admin
import logging

logger = logging.getLogger(__name__)

# Inisialisasi Firebase saat fungsi dimuat (cold start)
# Penting: Pastikan initialize_firebase_admin() hanya menginisialisasi sekali per instance
initialize_firebase_admin()

# Vercel akan secara otomatis mendeteksi objek 'app' ini
# sebagai aplikasi ASGI Anda. Tidak perlu Mangum di sini.