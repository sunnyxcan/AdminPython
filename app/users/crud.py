# app/users/crud.py

from sqlalchemy.orm import Session
from app.users import models, schemas
from app.roles import models as role_models # Impor model Role jika belum
# Hapus import uuid
# import uuid

def get_user(db: Session, user_uid: str):
    # PERBAIKAN: Hapus konversi UID ke objek UUID.
    # UID sekarang diperlakukan sebagai string.
    return db.query(models.User).filter(models.User.uid == user_uid).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    # PERBAIKAN: Hapus konversi UID ke objek UUID.
    # UID sekarang diperlakukan sebagai string.
    # uid_obj = uuid.UUID(user.uid) # Baris ini dihapus

    # Buat objek User model
    db_user = models.User(
        uid=user.uid, # Langsung gunakan user.uid (string)
        fullname=user.fullname,
        nickname=user.nickname,
        gender=user.gender,
        jabatan=user.jabatan,
        imageUrl=user.imageUrl,
        email=user.email,
        role_id=user.role_id,
        status=user.status,
        joinDate=user.joinDate,
        grupDate=user.grupDate,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def update_user(db: Session, user_uid: str, user_update: schemas.UserUpdate):
    # PERBAIKAN: Hapus konversi UID ke objek UUID.
    # UID sekarang diperlakukan sebagai string.
    # try:
    #     uid_obj = uuid.UUID(user_uid)
    # except ValueError:
    #     return None
    db_user = db.query(models.User).filter(models.User.uid == user_uid).first() # Gunakan user_uid langsung
    if not db_user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_uid: str):
    # PERBAIKAN: Hapus konversi UID ke objek UUID.
    # UID sekarang diperlakukan sebagai string.
    # try:
    #     uid_obj = uuid.UUID(user_uid)
    # except ValueError:
    #     return False
    db_user = db.query(models.User).filter(models.User.uid == user_uid).first() # Gunakan user_uid langsung
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False