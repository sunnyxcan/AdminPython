# app/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Admin Panel API"
    API_V1_STR: str = "/api"

    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # --- PERUBAHAN DI SINI ---
    # Mengubah nama variabel Python dan kunci os.getenv()
    # agar sesuai dengan nama variabel lingkungan di Netlify (FIREBASE_SERVICE_ACCOUNT_BASE64)
    FIREBASE_SERVICE_ACCOUNT_BASE64: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64")

    class Config:
        case_sensitive = True

settings = Settings()