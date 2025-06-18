# app/shift/routes.py (atau file router Anda)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime

from app.core.database import get_db
from app.shift import crud, schemas, models
from app.autentikasi.security import get_current_active_user as get_current_user
from app.users.schemas import UserDetail

router = APIRouter(
    prefix="/api/shifts",
    tags=["Shifts"],
)

# Endpoint untuk membuat data shift baru
@router.post("/", response_model=schemas.ShiftInDB, status_code=status.HTTP_201_CREATED)
def create_new_shift(
    shift: schemas.ShiftCreate, # <<< ShiftCreate mengandung jadwal
    db: Session = Depends(get_db),
    current_user: UserDetail = Depends(get_current_user)
):
    db_shift = crud.create_shift(db=db, shift=shift, createdBy_uid=current_user.uid)
    return db_shift

# Endpoint untuk mendapatkan semua data shift
@router.get("/", response_model=List[schemas.ShiftInDB])
def read_all_shifts(
    skip: int = 0,
    limit: int = 100,
    user_uid: Optional[UUID] = None, # Filter berdasarkan user_uid
    start_date: Optional[date] = None, # Filter berdasarkan tanggal mulai
    end_date: Optional[date] = None, # Filter berdasarkan tanggal akhir
    db: Session = Depends(get_db),
    current_user: UserDetail = Depends(get_current_user)
):
    """
    Mengambil daftar semua data shift dengan opsi filter.
    Membutuhkan autentikasi.
    """
    # =====================================================================
    # Perubahan di sini: Mengizinkan semua pengguna untuk melihat semua shift
    # =====================================================================

    # Jika user_uid disediakan, terapkan filter ini.
    # Namun, kita menghapus logika yang secara otomatis memfilter berdasarkan user_uid
    # pengguna saat ini jika mereka bukan admin.

    # Jika pengguna bukan admin dan user_uid yang diminta bukan user_uid mereka sendiri,
    # kita masih bisa membatasi akses jika Anda mau, tetapi tidak akan memfilter secara otomatis.
    # Contoh: Jika non-admin meminta user_uid orang lain, tetap blokir:
    if current_user.role.nama != "Admin" and user_uid is not None and current_user.uid != user_uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sebagai staff, Anda hanya dapat melihat shift milik Anda sendiri atau semua shift jika tidak ada filter user_uid."
        )

    # Catatan: Kita tidak lagi secara otomatis menimpa user_uid = current_user.uid
    # ini berarti jika user_uid adalah None, crud.get_shifts akan mendapatkan semua shift
    # (sesuai dengan limit dan filter tanggal).

    shifts = crud.get_shifts(db, skip=skip, limit=limit, user_uid=user_uid, start_date=start_date, end_date=end_date)
    return shifts

# Endpoint untuk mendapatkan data shift berdasarkan no
@router.get("/{shift_no}", response_model=schemas.ShiftInDB)
def read_shift_by_no(
    shift_no: int,
    db: Session = Depends(get_db),
    current_user: UserDetail = Depends(get_current_user)
):
    """
    Mengambil satu data shift berdasarkan nomor (no).
    Membutuhkan autentikasi.
    """
    db_shift = crud.get_shift(db, shift_no=shift_no)
    if db_shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift tidak ditemukan")

    # Otorisasi: Pastikan pengguna yang meminta shift adalah pemilik shift atau admin
    # TETAPKAN INI: Umumnya, membaca detail shift spesifik masih memerlukan otorisasi.
    if current_user.role.nama != "Admin" and db_shift.user_uid != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tidak memiliki izin untuk mengakses shift ini."
        )

    return db_shift

# Endpoint untuk memperbarui data shift
@router.put("/{shift_no}", response_model=schemas.ShiftInDB)
def update_existing_shift(
    shift_no: int,
    shift: schemas.ShiftUpdate, # <<< ShiftUpdate mengandung jadwal
    db: Session = Depends(get_db),
    current_user: UserDetail = Depends(get_current_user)
):
    db_shift = crud.get_shift(db, shift_no=shift_no)
    if db_shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift tidak ditemukan")

    updated_shift = crud.update_shift(db=db, shift_no=shift_no, shift_update=shift)
    return updated_shift

# Endpoint untuk menghapus data shift
@router.delete("/{shift_no}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_shift(
    shift_no: int,
    db: Session = Depends(get_db),
    current_user: UserDetail = Depends(get_current_user)
):
    """
    Menghapus data shift.
    Membutuhkan autentikasi. Hanya pemilik shift atau admin yang bisa menghapus.
    """
    db_shift = crud.get_shift(db, shift_no=shift_no)
    if db_shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift tidak ditemukan")

    # Otorisasi: Hanya pemilik shift atau admin yang bisa menghapus
    # TETAPKAN INI: Umumnya, penghapusan memerlukan otorisasi yang ketat.
    if current_user.role.nama != "Admin" and db_shift.user_uid != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tidak memiliki izin untuk menghapus shift ini."
        )

    crud.delete_shift(db=db, shift_no=shift_no)
    return {"message": "Shift berhasil dihapus"}