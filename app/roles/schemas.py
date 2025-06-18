# app/roles/schemas.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class RoleBase(BaseModel):
    # PERBAIKAN: Ubah 'name' menjadi 'nama' agar sesuai dengan model dan database
    nama: str
    deskripsi: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase):
    pass

class RoleInDB(RoleBase):
    id: int
    # Sesuaikan dengan nama kolom di database
    createOn: datetime
    modifiedOn: Optional[datetime] = None

    class Config:
        from_attributes = True # Ini adalah pengganti 'orm_mode = True' di Pydantic v2