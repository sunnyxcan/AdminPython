# app/roles/crud.py

from sqlalchemy.orm import Session
from app.roles import models, schemas

def get_role(db: Session, role_id: int):
    return db.query(models.Role).filter(models.Role.id == role_id).first()

def get_role_by_nama(db: Session, role_nama: str):
    # PERBAIKAN: Gunakan models.Role.nama
    return db.query(models.Role).filter(models.Role.nama == role_nama).first()

def get_roles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Role).offset(skip).limit(limit).all()

def create_role(db: Session, role: schemas.RoleCreate):
    # PERBAIKAN: Gunakan nama=role.nama
    db_role = models.Role(nama=role.nama, deskripsi=role.deskripsi)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

def update_role(db: Session, role_id: int, role: schemas.RoleUpdate):
    db_role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if db_role:
        # PERBAIKAN: role.model_dump() untuk Pydantic v2
        # Menggunakan exclude_unset=True agar hanya field yang disediakan di-update
        update_data = role.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_role, key, value)
        db.commit()
        db.refresh(db_role)
    return db_role

def delete_role(db: Session, role_id: int):
    db_role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if db_role:
        db.delete(db_role)
        db.commit()
    return db_role