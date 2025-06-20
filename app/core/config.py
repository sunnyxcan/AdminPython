# app/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Admin Panel API"
    API_V1_STR: str = "/api"

    DATABASE_URL: str = os.getenv("DATABASE_URL")
    # Hapus atau ganti ini jika kamu tidak lagi menggunakan path file
    # FIREBASE_SERVICE_ACCOUNT_KEY: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
    
    class Config:
        case_sensitive = True

settings = Settings()