# app/roles/models.py

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Role(Base):
    __tablename__ = "roles" # Nama tabel di database

    id = Column(Integer, primary_key=True, index=True)
    # PERBAIKAN: Ubah 'name' menjadi 'nama' agar sesuai dengan kolom di database Anda
    # Jika nama kolom di database Anda adalah 'nama', maka definisikan di sini sebagai 'nama'
    nama = Column(String, unique=True, index=True, nullable=False)
    deskripsi = Column(String, nullable=True)
    createOn = Column("createOn", DateTime(timezone=True), server_default=func.now())
    modifiedOn = Column("modifiedOn", DateTime(timezone=True), onupdate=func.now())