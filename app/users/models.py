# app/users/models.py
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.roles.models import Role

class User(Base):
    __tablename__ = "users"

    uid = Column(String, primary_key=True, index=True, unique=True, nullable=False)
    fullname = Column(String, nullable=False)
    nickname = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    jabatan = Column(String, nullable=True)
    imageUrl = Column("imageUrl", String, nullable=True)
    joinDate = Column("joinDate", Date, nullable=False)
    grupDate = Column("grupDate", Date, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    status = Column(String, nullable=False)
    createOn = Column("createOn", Date, server_default=func.current_date())
    modifiedOn = Column("modifiedOn", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Tambahan: Kolom FCM Token ---
    fcm_token = Column(String, nullable=True, unique=True, index=True)
    # ----------------------------------

    role = relationship("Role")
    izin = relationship("Izin", back_populates="user")

    dataTelat = relationship("DataTelat", foreign_keys="[DataTelat.user_uid]", back_populates="user")
    approved_dataTelat = relationship("DataTelat", foreign_keys="[DataTelat.by]", back_populates="approved_by")

    shift = relationship("Shift", back_populates="user", foreign_keys="[Shift.user_uid]")
    created_shifts = relationship("Shift", back_populates="created_by_user", foreign_keys="[Shift.createdBy_uid]")