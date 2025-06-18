# app/shift/models.py
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
# from sqlalchemy.dialects.postgresql import UUID # Hapus baris ini
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Shift(Base):
    __tablename__ = "dataShift" # Nama tabel di database

    no = Column(Integer, primary_key=True, index=True)
    # Mengubah user_uid dari UUID menjadi String
    user_uid = Column(String, ForeignKey('users.uid'), nullable=False)
    
    tanggalMulai = Column(Date, nullable=False)
    tanggalAkhir = Column(Date, nullable=False)
    
    jamMasuk = Column(DateTime(timezone=True), nullable=True)
    jamPulang = Column(DateTime(timezone=True), nullable=True)
    
    jamMasukDoubleShift = Column(DateTime(timezone=True), nullable=True)
    jamPulangDoubleShift = Column(DateTime(timezone=True), nullable=True)
    
    jadwal = Column(String, nullable=True)
    keterangan = Column(String, nullable=True)
    
    # Mengubah createdBy_uid dari UUID menjadi String
    createdBy_uid = Column(String, ForeignKey('users.uid'), nullable=False) 
    
    createOn = Column(DateTime(timezone=True), server_default=func.now())
    modifiedOn = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="shift", foreign_keys=[user_uid])
    created_by_user = relationship("User", foreign_keys=[createdBy_uid], back_populates="created_shifts")

    def __repr__(self):
        return f"<Shift(no={self.no}, user_uid='{self.user_uid}', tanggalMulai='{self.tanggalMulai}')>"