# app/autentikasi/crud.py

from sqlalchemy.orm import Session
from app.users import models as user_models
from app.users import schemas as user_schemas

def get_current_user_from_db(db: Session, user_uid: str):
    """
    Mengambil data pengguna dari database berdasarkan UID Supabase.
    """
    return user_models.User.get_user(db, user_uid=user_uid)

# Jika Anda ingin menyimpan informasi sesi atau token di backend, Anda bisa menambahkannya di sini.
# Namun, untuk kasus ini, kita akan mengandalkan JWT dari Supabase di frontend.