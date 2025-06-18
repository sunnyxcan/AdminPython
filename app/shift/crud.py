# app/shift/crud.py
from sqlalchemy.orm import Session, joinedload # Import joinedload
from sqlalchemy import func
from app.shift import models, schemas
from uuid import UUID
from datetime import date, datetime

def get_shift(db: Session, shift_no: int):
    """
    Mengambil satu data shift berdasarkan nomor (no) dengan eager loading relasi user.
    """
    return db.query(models.Shift)\
             .options(joinedload(models.Shift.user))\
             .options(joinedload(models.Shift.created_by_user))\
             .filter(models.Shift.no == shift_no).first()

def get_shifts(db: Session, skip: int = 0, limit: int = 100, user_uid: UUID = None, start_date: date = None, end_date: date = None):
    """
    Mengambil daftar data shift dengan opsi filter dan paginasi,
    serta eager loading relasi user dan created_by_user.
    """
    query = db.query(models.Shift)\
              .options(joinedload(models.Shift.user))\
              .options(joinedload(models.Shift.created_by_user)) # Tambahkan ini

    if user_uid:
        query = query.filter(models.Shift.user_uid == user_uid)
    if start_date:
        query = query.filter(models.Shift.tanggalMulai >= start_date)
    if end_date:
        query = query.filter(models.Shift.tanggalAkhir <= end_date)
        
    return query.offset(skip).limit(limit).all()

def create_shift(db: Session, shift: schemas.ShiftCreate, createdBy_uid: UUID):
    """
    Membuat data shift baru.
    """
    db_shift = models.Shift(**shift.model_dump(), createdBy_uid=createdBy_uid)
    db.add(db_shift)
    db.commit()
    db.refresh(db_shift)
    # Setelah membuat, kita juga ingin meload relasi agar respons sesuai
    db_shift = db.query(models.Shift)\
                 .options(joinedload(models.Shift.user))\
                 .options(joinedload(models.Shift.created_by_user))\
                 .filter(models.Shift.no == db_shift.no).first()
    return db_shift

def update_shift(db: Session, shift_no: int, shift_update: schemas.ShiftUpdate):
    """
    Memperbarui data shift yang ada.
    """
    db_shift = db.query(models.Shift).filter(models.Shift.no == shift_no).first()
    if db_shift:
        update_data = shift_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_shift, key, value)
        
        db.commit()
        db.refresh(db_shift)
        # Setelah update, kita juga ingin meload relasi agar respons sesuai
        db_shift = db.query(models.Shift)\
                     .options(joinedload(models.Shift.user))\
                     .options(joinedload(models.Shift.created_by_user))\
                     .filter(models.Shift.no == db_shift.no).first()
    return db_shift

def delete_shift(db: Session, shift_no: int):
    """
    Menghapus data shift berdasarkan nomor (no).
    """
    db_shift = db.query(models.Shift).filter(models.Shift.no == shift_no).first()
    if db_shift:
        db.delete(db_shift)
        db.commit()
        return db_shift
    return None