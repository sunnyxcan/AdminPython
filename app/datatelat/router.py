# app/datatelat/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db, Base, engine
from app.datatelat import schemas, crud, models

from app.users.crud import get_user as get_user_by_uid
from app.dataizin.crud import get_izin as get_izin_by_no

# Import yang diperlukan untuk autentikasi dan otorisasi
from app.autentikasi.security import verify_firebase_token, get_admin_user_token, get_current_active_user # --- TAMBAHKAN get_current_active_user DI SINI ---
from app.users.schemas import UserInDB

import logging
from sqlalchemy import inspect

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/api/datatelat",
    tags=["Data-Telat"],
    responses={404: {"description": "Data Telat tidak ditemukan"}},
)

@router.on_event("startup")
async def create_datatelat_table():
    models.Base.metadata.create_all(bind=engine)
    print("Tabel 'dataTelat' dipastikan ada atau dibuat.")

@router.post("/", response_model=schemas.DataTelatInDB, status_code=status.HTTP_201_CREATED)
def create_new_dataTelat(
    dataTelat_data: schemas.DataTelatCreate,
    db: Session = Depends(get_db)
):
    user_exists = get_user_by_uid(db, user_uid=dataTelat_data.user_uid)
    if not user_exists:
        raise HTTPException(status_code=400, detail="Pengguna dengan UID yang diberikan tidak ditemukan.")

    izin_exists = get_izin_by_no(db, izin_no=dataTelat_data.izin_no)
    if not izin_exists:
        raise HTTPException(status_code=400, detail=f"Data Izin dengan nomor {dataTelat_data.izin_no} tidak ditemukan.")

    existing_dataTelat_for_izin = db.query(models.DataTelat).filter(models.DataTelat.izin_no == dataTelat_data.izin_no).first()
    if existing_dataTelat_for_izin:
        raise HTTPException(status_code=409, detail=f"Data Telat untuk Izin nomor {dataTelat_data.izin_no} sudah ada.")

    return crud.create_dataTelat(db=db, dataTelat=dataTelat_data)

@router.get("/{dataTelat_no}", response_model=schemas.DataTelatInDB)
def get_single_dataTelat(
    dataTelat_no: int,
    db: Session = Depends(get_db)
):
    db_dataTelat = crud.get_dataTelat(db, dataTelat_no)
    if db_dataTelat is None:
        raise HTTPException(status_code=404, detail="Data Telat tidak ditemukan")
    return db_dataTelat

@router.get("/", response_model=List[schemas.DataTelatInDB])
def get_all_dataTelat(
    tahun: Optional[int] = Query(None, description="Filter data telat berdasarkan tahun Izin"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    dataTelat_list = crud.get_list_dataTelat(db, skip=skip, limit=limit, tahun=tahun)
    return dataTelat_list

@router.put("/{dataTelat_no}", response_model=schemas.DataTelatInDB)
def update_existing_dataTelat(
    dataTelat_no: int,
    dataTelat_update: schemas.DataTelatUpdate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    db_dataTelat = crud.update_dataTelat(
        db,
        dataTelat_no=dataTelat_no,
        dataTelat_update=dataTelat_update,
        current_user_uid=current_user.uid
    )
    if db_dataTelat is None:
        raise HTTPException(status_code=404, detail="Data Telat tidak ditemukan")
    return db_dataTelat

@router.delete("/{dataTelat_no}", status_code=status.HTTP_200_OK)
def delete_existing_dataTelat(
    dataTelat_no: int,
    db: Session = Depends(get_db)
):
    is_deleted = crud.delete_dataTelat(db, dataTelat_no=dataTelat_no)
    if not is_deleted:
        raise HTTPException(status_code=404, detail="Data Telat tidak ditemukan")
    return {"message": "Data Telat berhasil dihapus"}

# --- FUNGSI TRIGGER TRANSFER DATA LAMA BARU ---
@router.post("/transfer-old-data/", status_code=status.HTTP_200_OK)
async def trigger_transfer_old_data_telat(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(verify_firebase_token)
):
    # Memastikan hanya admin yang bisa memicu
    get_admin_user_token(current_user_token) # Menggunakan fungsi get_admin_user_token langsung

    logger.info("Memulai pemindahan data telat lama secara manual...")
    background_tasks.add_task(crud.transfer_old_data_telat_to_archive_v2, db)
    return {"message": "Proses pemindahan data telat lama telah dimulai di latar belakang."}

# --- FUNGSI MENDAPATKAN DATA ARSIP BARU ---
@router.get("/archive/{year}", response_model=List[schemas.DataTelatInDB])
def get_archived_data_telat_by_year(
    year: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(verify_firebase_token)
):
    # Memastikan hanya admin yang bisa mengakses arsip
    get_admin_user_token(current_user_token)

    archive_table_name = f"dataTelat_{year}"
    DynamicDataTelatModel = models.DataTelat.create_dynamic_table_model(archive_table_name)

    inspector = inspect(db.bind)
    if not inspector.has_table(archive_table_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tabel arsip '{archive_table_name}' tidak ditemukan.")

    # Menggunakan joinedload untuk memuat relasi user, izin, dan approved_by
    archived_datatelat = db.query(DynamicDataTelatModel)\
        .options(joinedload(DynamicDataTelatModel.user),
                 joinedload(DynamicDataTelatModel.izin),
                 joinedload(DynamicDataTelatModel.approved_by))\
        .offset(skip).limit(limit).all()

    # Konversi waktu ke GMT+7 untuk 'jam' jika ada
    for data_telat in archived_datatelat:
        if data_telat.createOn:
            data_telat.createOn = crud.get_local_datetime_gmt7(data_telat.createOn)
        if data_telat.modifiedOn:
            data_telat.modifiedOn = crud.get_local_datetime_gmt7(data_telat.modifiedOn)

        # Khusus untuk jamKeluar dan jamKembali di objek izin terkait
        if data_telat.izin:
            if data_telat.izin.jamKeluar:
                data_telat.izin.jamKeluar = crud.get_local_datetime_gmt7(data_telat.izin.jamKeluar)
            if data_telat.izin.jamKembali:
                data_telat.izin.jamKembali = crud.get_local_datetime_gmt7(data_telat.izin.jamKembali)

    return archived_datatelat