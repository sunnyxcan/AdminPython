# app/users/schemas.py

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import Optional
from app.roles.schemas import RoleInDB

# --- Skema baru untuk detail pengguna singkat ---
class UserDetail(BaseModel):
    fullname: str
    jabatan: Optional[str] = None
    imageUrl: Optional[str] = None
    # Jika ingin fcm_token muncul di UserDetail juga, tambahkan di sini
    # fcm_token: Optional[str] = None 

    class Config:
        from_attributes = True
# -----------------------------------------------

class UserBase(BaseModel):
    fullname: str
    nickname: Optional[str] = None
    gender: Optional[str] = None
    jabatan: Optional[str] = None
    imageUrl: Optional[str] = None
    email: EmailStr
    role_id: int
    status: str
    joinDate: date
    grupDate: date
    tanggalAkhirCuti: Optional[date] = None


# --- Definisi UserCreateByAdmin yang Anda berikan ---
class UserCreateByAdmin(BaseModel):
    email: str = Field(..., example="newuser@example.com")
    password: str = Field(..., min_length=6, example="password123")
    imageUrl: Optional[str] = None
    fullname: str
    nickname: Optional[str] = None
    gender: str
    jabatan: str
    joinDate: date
    grupDate: date
    role_id: int
    status: str
    tanggalAkhirCuti: Optional[date] = None
# ---------------------------------------------------

class UserCreate(UserBase):
    uid: str
    pass

class UserUpdate(BaseModel):
    fullname: Optional[str] = None
    nickname: Optional[str] = None
    gender: Optional[str] = None
    jabatan: Optional[str] = None
    imageUrl: Optional[str] = None
    email: Optional[EmailStr] = None
    role_id: Optional[int] = None
    status: Optional[str] = None
    joinDate: Optional[date] = None
    grupDate: Optional[date] = None
    tanggalAkhirCuti: Optional[date] = None
    # --- Tambahan: Kolom FCM Token ---
    fcm_token: Optional[str] = None
    # ----------------------------------

class UserInDB(UserBase):
    uid: str
    createOn: date
    modifiedOn: Optional[datetime] = None
    role: RoleInDB
    # --- Tambahan: Kolom FCM Token ---
    fcm_token: Optional[str] = None
    # ----------------------------------

    class Config:
        from_attributes = True