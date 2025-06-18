# app/shift/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional
import uuid

# Import skema UserInDB untuk menyertakan detail user saat mengambil data shift
from app.users.schemas import UserInDB # Ganti UserDetail dengan UserInDB
from app.users.schemas import UserDetail # Ini tetap bisa ada jika ada penggunaan lain

class ShiftBase(BaseModel):
    user_uid: uuid.UUID
    tanggalMulai: date
    tanggalAkhir: date
    jamMasuk: Optional[datetime] = None
    jamPulang: Optional[datetime] = None
    jamMasukDoubleShift: Optional[datetime] = None
    jamPulangDoubleShift: Optional[datetime] = None
    jadwal: Optional[str] = None
    keterangan: Optional[str] = None

class ShiftCreate(ShiftBase):
    pass 

class ShiftUpdate(BaseModel):
    user_uid: Optional[uuid.UUID] = None
    tanggalMulai: Optional[date] = None
    tanggalAkhir: Optional[date] = None
    jamMasuk: Optional[datetime] = None
    jamPulang: Optional[datetime] = None
    jamMasukDoubleShift: Optional[datetime] = None
    jamPulangDoubleShift: Optional[datetime] = None
    jadwal: Optional[str] = None
    keterangan: Optional[str] = None

class ShiftInDB(ShiftBase):
    no: int
    createdBy_uid: uuid.UUID
    createOn: datetime
    modifiedOn: Optional[datetime] = None
    
    # --- PERBAIKAN DI SINI ---
    user_detail: Optional[UserInDB] = Field(None, alias='user') # Ganti UserDetail dengan UserInDB
    created_by_user_detail: Optional[UserInDB] = Field(None, alias='created_by_user') # Ganti UserDetail dengan UserInDB
    # -----------------------

    class Config:
        from_attributes = True
        populate_by_name = True