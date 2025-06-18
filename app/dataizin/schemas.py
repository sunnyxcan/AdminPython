# app/dataizin/schemas.py (Revisi Akhir)
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional

# Import skema UserDetail yang baru
from app.users.schemas import UserDetail 

class IzinBase(BaseModel):
    user_uid: str
    tanggal: date = Field(default_factory=date.today)
    jamKeluar: Optional[datetime] = None
    ipKeluar: Optional[str] = None
    jamKembali: Optional[datetime] = None
    ipKembali: Optional[str] = None

class IzinCreate(IzinBase):
    pass

class IzinUpdate(BaseModel):
    user_uid: Optional[str] = None
    durasi: Optional[str] = None 
    status: Optional[str] = None 
    tanggal: Optional[date] = None
    jamKeluar: Optional[datetime] = None
    ipKeluar: Optional[str] = None
    jamKembali: Optional[datetime] = None
    ipKembali: Optional[str] = None

class IzinInDB(IzinBase):
    no: int
    durasi: Optional[str] = None
    status: str
    createOn: datetime
    modifiedOn: Optional[datetime] = None
    
    user_detail: Optional[UserDetail] = Field(None, alias='user') 

    class Config:
        from_attributes = True
        populate_by_name = True