# backend/netlify/functions/api/main.py
import os
from mangum import Mangum
from app.main import app # Sesuaikan jika lokasi app Anda berbeda

# Ini penting untuk inisialisasi Firebase di lingkungan fungsi
# dari variabel lingkungan FIREBASE_SERVICE_ACCOUNT_BASE64
from app.core.firebase import initialize_firebase_admin

# Inisialisasi Firebase saat fungsi dimuat (cold start)
initialize_firebase_admin()

# Wrapper Mangum untuk aplikasi FastAPI Anda
handler = Mangum(app)