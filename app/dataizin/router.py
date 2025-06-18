# app/dataizin/router.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date, timezone, timedelta

from app.core.database import get_db, Base, engine
from app.dataizin import schemas, crud, models
from app.users.crud import get_user as get_user_by_uid

from app.datatelat import crud as datatelat_crud

from app.autentikasi.security import verify_firebase_token, get_admin_user_token
from app.dataizin import crud as crud_data_izin
from app.core.fcm import send_fcm_notification_to_all_users, send_fcm_notification_to_single_user

import logging
from pydantic import Field
from sqlalchemy import inspect

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/api/dataizin",
    tags=["Data-Izin"],
    responses={404: {"deskripsi": "Izin tidak ditemukan"}},
)

@router.on_event("startup")
async def create_izin_table():
    models.Base.metadata.create_all(bind=engine)
    print("Tabel 'dataIzin' dipastikan ada atau dibuat.")

def get_current_user_uid_placeholder(user_uid: str = Query(..., description="UID pengguna saat ini (placeholder)")) -> str:
    return user_uid

@router.post("/", response_model=schemas.IzinInDB, status_code=status.HTTP_201_CREATED)
async def create_izin_keluar(
    izin_data: schemas.IzinCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user_exists = get_user_by_uid(db, user_uid=izin_data.user_uid)
    if not user_exists:
        raise HTTPException(status_code=400, detail="Pengguna dengan UID yang diberikan tidak ditemukan.")

    # --- Validasi Tambahan: Cek apakah ada izin pending untuk user ini ---
    existing_pending_izin = crud.get_pending_izin_by_user(db, izin_data.user_uid)
    if existing_pending_izin:
        raise HTTPException(
            status_code=400,
            detail="Anda masih memiliki izin keluar yang belum diakhiri (status Pending)."
        )
    # --- Akhir Validasi Tambahan ---

    now_utc = datetime.now(timezone.utc)
    current_time_gmt7 = crud.get_local_datetime_gmt7(now_utc)

    day_of_week = current_time_gmt7.weekday()
    MAX_DAILY_IZIN = 4
    if day_of_week == 4: # Hari Jumat (0=Senin, 4=Jumat)
        MAX_DAILY_IZIN = 6

    current_izin_count = crud.get_izin_count_for_today(db, izin_data.user_uid)

    if current_izin_count >= MAX_DAILY_IZIN:
        user_name = user_exists.fullname if user_exists and user_exists.fullname else "Staff"
        raise HTTPException(
            status_code=403,
            detail=f"{user_name} telah mencapai batas harian {MAX_DAILY_IZIN}X izin untuk hari ini."
        )

    if not izin_data.jamKeluar:
        izin_data.jamKeluar = datetime.now(timezone.utc)

    db_dataIzin = crud.create_izin(db=db, izin=izin_data)

    # --- Panggil Notifikasi FCM untuk Izin Keluar ---
    user_name = user_exists.fullname if user_exists and user_exists.fullname else "Seorang pengguna"
    title = "Izin Keluar Baru!"
    body = f"{user_name} baru saja memulai izin keluar."
    
    # Tambahkan background task untuk mengirim notifikasi
    background_tasks.add_task(
        send_fcm_notification_to_all_users, 
        db_session=db, 
        title=title, 
        body=body, 
        data={"type": "izin_keluar", "izin_no": str(db_dataIzin.no), "user_uid": db_dataIzin.user_uid}
    )
    # --- Akhir Notifikasi FCM ---

    return db_dataIzin

class IzinKembaliPayload(schemas.BaseModel):
    jamKembali: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ipKembali: Optional[str] = None

@router.post("/{izin_no}/kembali/", response_model=schemas.IzinInDB)
async def create_izin_kembali(
    izin_no: int,
    payload: IzinKembaliPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # --- Validasi Tambahan: Cek status izin sebelum update ---
    db_dataIzin_to_check = crud.get_izin_by_no(db, izin_no)
    if not db_dataIzin_to_check:
        raise HTTPException(status_code=404, detail="Izin tidak ditemukan.")
    
    if db_dataIzin_to_check.status != "Pending":
        raise HTTPException(
            status_code=400,
            detail=f"Izin dengan nomor {izin_no} tidak dalam status 'Pending'. Status saat ini: {db_dataIzin_to_check.status}."
        )
    # --- Akhir Validasi Tambahan ---

    db_dataIzin = crud.update_izin_kembali(db, izin_no, payload.jamKembali, payload.ipKembali)
    # Pemeriksaan db_dataIzin is None ini masih relevan jika update_izin_kembali mengembalikan None
    # karena alasan lain (misalnya, masalah database internal setelah lolos validasi status).
    if db_dataIzin is None:
        raise HTTPException(status_code=500, detail="Gagal memperbarui izin kembali. Silakan coba lagi.")


    user_detail = get_user_by_uid(db, db_dataIzin.user_uid)

    if db_dataIzin.status == "Lewat Waktu":
        try:
            existing_datatelat = db.query(datatelat_crud.models.DataTelat).filter(datatelat_crud.models.DataTelat.izin_no == db_dataIzin.no).first()
            if not existing_datatelat:
                datatelat_create_schema = datatelat_crud.schemas.DataTelatCreate(
                    izin_no=db_dataIzin.no,
                    user_uid=db_dataIzin.user_uid,
                    by="Sistem",
                    keterangan="Otomatis dicatat karena izin kembali lewat waktu.",
                    status="Pending"
                )
                datatelat_entry = datatelat_crud.create_dataTelat(db=db, dataTelat=datatelat_create_schema)
                logger.info(f"Data Telat otomatis dicatat untuk Izin no: {db_dataIzin.no}, Sanksi: {datatelat_entry.sanksi}, Denda: {datatelat_entry.denda}")
            else:
                logger.info(f"Data Telat untuk Izin no: {db_dataIzin.no} sudah ada, tidak membuat entri baru.")
        except Exception as e:
            logger.error(f"Gagal mencatat Data Telat untuk Izin no {db_dataIzin.no}: {e}")

    # --- Panggil Notifikasi FCM untuk Izin Kembali ---
    user_name = user_detail.fullname if user_detail and user_detail.fullname else "Seorang pengguna"
    
    if db_dataIzin.status == "Lewat Waktu":
        title = "Izin Kembali Lewat Waktu!"
        body = f"{user_name} telah kembali dari izin dengan status 'Lewat Waktu'. Durasi: {db_dataIzin.durasi}"
        # ... (logika pencatatan data telat)
    else:
        title = "Izin Kembali Tepat Waktu!"
        body = f"{user_name} telah kembali dari izin dengan status 'Tepat Waktu'. Durasi: {db_dataIzin.durasi}"

    # Tambahkan background task untuk mengirim notifikasi
    background_tasks.add_task(
        send_fcm_notification_to_all_users, 
        db_session=db, 
        title=title, 
        body=body, 
        data={"type": "izin_kembali", "izin_no": str(db_dataIzin.no), "user_uid": db_dataIzin.user_uid, "status": db_dataIzin.status}
    )
    # --- Akhir Notifikasi FCM ---

    return db_dataIzin

@router.get("/pending_izin/", response_model=Optional[schemas.IzinInDB])
def get_pending_izin(
    user_uid: str = Depends(get_current_user_uid_placeholder),
    db: Session = Depends(get_db)
):
    izin = crud.get_pending_izin_by_user(db, user_uid)
    return izin

@router.get("/", response_model=List[schemas.IzinInDB])
def get_izin_history(
    user_uid: str = Depends(get_current_user_uid_placeholder),
    tanggal: Optional[date] = Query(None, description="Filter izin berdasarkan tanggal (YYYY-MM-DD) di GMT+7"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    izins = crud.get_izin_history_by_user(db, user_uid, tanggal, skip=skip, limit=limit)
    return izins

@router.get("/all-pending/", response_model=List[schemas.IzinInDB])
def get_all_pending_izin_staff(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    izins = crud.get_all_pending_izins(db, skip=skip, limit=limit)
    return izins

@router.get("/all-history/", response_model=List[schemas.IzinInDB])
def get_all_izins_history_endpoint(
    tanggal: Optional[date] = Query(None, description="Filter semua izin berdasarkan tanggal (YYYY-MM-DD) di GMT+7"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    izins = crud.get_all_izins_history(db, tanggal, skip, limit)
    return izins

@router.get("/{izin_no}/", response_model=schemas.IzinInDB)
def get_izin_by_id(
    izin_no: int,
    db: Session = Depends(get_db)
):
    """
    Mengambil detail izin berdasarkan nomor izin.
    """
    izin = crud.get_izin_by_no(db, izin_no)
    if izin is None:
        raise HTTPException(status_code=404, detail="Izin tidak ditemukan.")
    return izin

@router.put("/{izin_no}", response_model=schemas.IzinInDB)
def update_existing_izin(izin_no: int, izin: schemas.IzinUpdate, db: Session = Depends(get_db)):
    if izin.user_uid:
        user_exists = get_user_by_uid(db, user_uid=izin.user_uid)
        if not user_exists:
            raise HTTPException(status_code=400, detail="Pengguna dengan UID yang diberikan tidak ditemukan.")

    db_dataIzin = crud.update_izin(db, izin_no=izin_no, izin_update=izin)
    if db_dataIzin is None:
        raise HTTPException(status_code=404, detail="Izin tidak ditemukan")
    return db_dataIzin

@router.delete("/{izin_no}", status_code=status.HTTP_200_OK)
def delete_existing_izin(izin_no: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_izin(db, izin_no=izin_no)
    if not is_deleted:
        raise HTTPException(status_code=404, detail="Izin tidak ditemukan")
    return {"message": "Izin berhasil dihapus"}

### Fungsi Trigger Transfer Data Lama
@router.post("/transfer-old-data/", status_code=status.HTTP_200_OK)
async def trigger_transfer_old_data_izin(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(verify_firebase_token)
):
    await get_admin_user_token(current_user_token)

    logger.info("Memulai pemindahan data izin lama secara manual...")
    # Pastikan fungsi ini tersedia di crud_data_izin dan sesuai dengan tanda tangan
    background_tasks.add_task(crud_data_izin.transfer_old_data_izin_to_archive, db)
    return {"message": "Proses pemindahan data izin lama telah dimulai di latar belakang."}

@router.get("/archive/{year}", response_model=List[schemas.IzinInDB])
def get_archived_data_izin_by_year(
    year: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(verify_firebase_token)
):
    get_admin_user_token(current_user_token)

    archive_table_name = f"dataIzin_{year}"
    DynamicDataIzinModel = models.Izin.create_dynamic_table_model(archive_table_name)

    inspector = inspect(db.bind)
    if not inspector.has_table(archive_table_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tabel arsip '{archive_table_name}' tidak ditemukan.")

    # Menggunakan joinedload untuk memuat relasi user
    archived_izins = db.query(DynamicDataIzinModel).options(joinedload(DynamicDataIzinModel.user)).offset(skip).limit(limit).all()

    # Konversi waktu ke GMT+7 untuk setiap objek izin yang diarsipkan
    for izin in archived_izins:
        if izin.jamKeluar: # Hanya konversi jika tidak None
            izin.jamKeluar = crud_data_izin.get_local_datetime_gmt7(izin.jamKeluar)
        if izin.jamKembali: # Hanya konversi jika tidak None
            izin.jamKembali = crud_data_izin.get_local_datetime_gmt7(izin.jamKembali)

    return archived_izins