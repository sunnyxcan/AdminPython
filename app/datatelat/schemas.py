# app/datatelat/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional

# Import skema UserDetail jika Anda ingin menampilkan detail pengguna terkait
from app.users.schemas import UserDetail
# Import skema IzinInDB untuk menampilkan detail izin terkait
from app.dataizin.schemas import IzinInDB

class DataTelatBase(BaseModel):
    izin_no: int
    user_uid: str

    by: Optional[str] = None
    keterangan: Optional[str] = None
    sanksi: Optional[str] = None
    denda: Optional[str] = None
    status: Optional[str] = None
    jam: Optional[str] = None

class DataTelatCreate(DataTelatBase):
    pass

class DataTelatUpdate(BaseModel):
    by: Optional[str] = None
    keterangan: Optional[str] = None
    sanksi: Optional[str] = None
    denda: Optional[str] = None
    status: Optional[str] = None
    jam: Optional[str] = None

class DataTelatInDB(DataTelatBase):
    no: int
    createOn: datetime
    modifiedOn: Optional[datetime] = None

    # Alias untuk relasi SQLAlchemy 'user'
    user: Optional[UserDetail] = Field(None, alias='user')
    # Alias untuk relasi SQLAlchemy 'izin'
    izin: Optional[IzinInDB] = Field(None, alias='izin')
    # TAMBAHKAN INI: Alias untuk relasi SQLAlchemy 'approved_by'
    approved_by: Optional[UserDetail] = Field(None, alias='approved_by')

    class Config:
        from_attributes = True
        populate_by_name = True