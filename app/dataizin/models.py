# app/dataizin/models.py

from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Izin(Base):
    __tablename__ = "dataIzin"
    no = Column(Integer, primary_key=True, index=True)
    user_uid = Column(String, ForeignKey('users.uid'), nullable=False)
    tanggal = Column(Date, default=func.current_date())
    jamKeluar = Column(DateTime(timezone=True), nullable=True)
    ipKeluar = Column(String, nullable=True)
    jamKembali = Column(DateTime(timezone=True), nullable=True)
    ipKembali = Column(String, nullable=True)
    durasi = Column(String, nullable=True)
    status = Column(String, default="Pending")
    createOn = Column(DateTime(timezone=True), server_default=func.now())
    modifiedOn = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="izin")
    dataTelat = relationship("DataTelat", back_populates="izin", uselist=False)

    def __repr__(self):
        return f"<Izin(no={self.no}, user_uid='{self.user_uid}', tanggal='{self.tanggal}')>"

    @classmethod
    def create_dynamic_table_model(cls, table_name: str):
        class DynamicDataIzin(cls):
            __tablename__ = table_name
            __table_args__ = ({'extend_existing': True},)
            # Menambahkan kembali relasi user untuk model dinamis
            user = relationship("User", foreign_keys=[cls.user_uid], primaryjoin=lambda: cls.user_uid == cls.user.uid, uselist=False)


        return DynamicDataIzin