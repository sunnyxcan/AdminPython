# app/datatelat/models.py
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

# --- TAMBAHKAN IMPOR INI ---
from app.dataizin.models import Izin
from app.users.models import User
# --- AKHIR TAMBAH IMPOR ---

class DataTelat(Base):
    __tablename__ = "dataTelat"
    no = Column(Integer, primary_key=True, index=True)

    # Menghubungkan ke tabel dataIzin.no
    izin_no = Column(Integer, ForeignKey('dataIzin.no'), unique=True, nullable=False)

    # Mengubah user_uid menjadi String
    user_uid = Column(String, ForeignKey('users.uid'), nullable=False)

    sanksi = Column(String, nullable=True)
    denda = Column(String, nullable=True)
    status = Column(String, default="Pending")

    keterangan = Column(String, nullable=True)
    jam = Column(String, nullable=True)

    # Mengubah 'by' menjadi String
    by = Column(String, ForeignKey('users.uid'), nullable=True)

    createOn = Column(DateTime(timezone=True), server_default=func.now())
    modifiedOn = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relasi ke model Izin (dataIzin)
    izin = relationship("Izin", back_populates="dataTelat")

    # Relasi ke model User (pemilik data telat)
    user = relationship("User", foreign_keys=[user_uid], back_populates="dataTelat", remote_side='User.uid')

    # Relasi ke model User untuk kolom 'by'
    approved_by = relationship("User", foreign_keys=[by], back_populates="approved_dataTelat", remote_side='User.uid')

    def __repr__(self):
        return f"<DataTelat(no={self.no}, izin_no={self.izin_no}, status='{self.status}', by={self.by})>"

    @classmethod
    def create_dynamic_table_model(cls, table_name: str):
        class DynamicDataTelat(cls):
            __tablename__ = table_name
            __table_args__ = ({'extend_existing': True},)

            no = Column(Integer, primary_key=True, index=True)

            # Penting: mendefinisikan ulang relasi untuk model dinamis
            # Pastikan foreign_keys menunjuk ke kolom dari `cls` (model asli)
            # Dan primaryjoin menunjuk ke kolom dari `cls` (model asli) juga
            izin = relationship("Izin", foreign_keys=[cls.izin_no], primaryjoin=lambda: cls.izin_no == Izin.no, uselist=False)
            user = relationship("User", foreign_keys=[cls.user_uid], primaryjoin=lambda: cls.user_uid == User.uid, remote_side='User.uid')
            approved_by = relationship("User", foreign_keys=[cls.by], primaryjoin=lambda: cls.by == User.uid, remote_side='User.uid')


        return DynamicDataTelat