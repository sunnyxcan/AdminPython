# app/datatelat/crud.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import extract, String
from app.datatelat import models, schemas
from datetime import datetime, timedelta, date, timezone
from typing import Optional, List # Tambahkan List

# Import model Izin dan User untuk mengakses data terkait
from app.dataizin.models import Izin # Pastikan ini diimpor
from app.users.models import User # Pastikan ini diimpor

from fastapi import HTTPException, status

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GMT7_TIMEZONE = timezone(timedelta(hours=7)) # Pastikan ini didefinisikan

def get_local_datetime_gmt7(dt_utc: datetime) -> datetime:
    """Mengonversi datetime UTC menjadi datetime dengan zona waktu GMT+7."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)

    gmt7_offset = timedelta(hours=7)
    gmt7_timezone = timezone(gmt7_offset)

    return dt_utc.astimezone(gmt7_timezone)

def calculate_duration_and_penalties(jamKeluar: datetime, jamKembali: datetime) -> tuple[str, str, str]:
    """
    Menghitung durasi keterlambatan, sanksi, dan denda.
    Asumsi: jamKeluar dan jamKembali sudah dalam zona waktu yang sama atau sudah UTC aware.
    Kita akan mengonversi ke UTC untuk perhitungan yang konsisten jika belum aware.
    """
    jam_keluar_aware = jamKeluar if jamKeluar.tzinfo is not None else jamKeluar.replace(tzinfo=timezone.utc)
    jam_kembali_aware = jamKembali if jamKembali is not None and jamKembali.tzinfo is not None else jamKembali.replace(tzinfo=timezone.utc)

    delta = jam_kembali_aware - jam_keluar_aware
    total_seconds = int(delta.total_seconds())

    over_time_seconds = max(0, total_seconds - (15 * 60)) # Lewat 15 menit

    hours = over_time_seconds // 3600
    minutes = (over_time_seconds % 3600) // 60
    seconds = over_time_seconds % 60

    duration_parts = []
    if hours > 0:
        duration_parts.append(f"{hours} Jam")
    if minutes > 0:
        duration_parts.append(f"{minutes} Menit")
    if seconds > 0:
        duration_parts.append(f"{seconds} Detik")

    durasi_str = "0 Detik" if not duration_parts else " ".join(duration_parts)

    sanksi = ""
    denda = "0"

    if over_time_seconds > 0:
        if over_time_seconds <= (3 * 60): # Telat dibawah atau sama dengan 3 menit dari batas 15 menit
            sanksi = "Kutip sampah"
        else: # Telat di atas 3 menit dari batas 15 menit
            sanksi = "Kutip sampah / Bersihkan PC / Bersihkan meja"
            denda = "300" # Denda dalam string
    
    return durasi_str, sanksi, denda

# --- CRUD Functions for DataTelat ---

def get_dataTelat(db: Session, dataTelat_no: int):
    return db.query(models.DataTelat).options(
        joinedload(models.DataTelat.user),
        joinedload(models.DataTelat.izin),
        joinedload(models.DataTelat.approved_by)
    ).filter(models.DataTelat.no == dataTelat_no).first()

def get_list_dataTelat(db: Session, skip: int = 0, limit: int = 100, tahun: Optional[int] = None):
    query = db.query(models.DataTelat).options(
        joinedload(models.DataTelat.user),
        joinedload(models.DataTelat.izin),
        joinedload(models.DataTelat.approved_by)
    )

    if tahun is not None:
        query = query.join(Izin, models.DataTelat.izin_no == Izin.no)
        query = query.filter(extract('year', Izin.tanggal) == tahun)

    query = query.order_by(Izin.tanggal.desc(), models.DataTelat.createOn.desc())
    return query.offset(skip).limit(limit).all()

def create_dataTelat(db: Session, dataTelat: schemas.DataTelatCreate):
    db_izin = db.query(Izin).filter(Izin.no == dataTelat.izin_no).first()
    if not db_izin:
        raise ValueError("Data Izin dengan nomor yang diberikan tidak ditemukan.")

    jam_keluar_from_izin = db_izin.jamKeluar
    jam_kembali_from_izin = db_izin.jamKembali

    calculated_durasi = None
    calculated_sanksi = None
    calculated_denda = None

    if jam_keluar_from_izin and jam_kembali_from_izin:
        calculated_durasi, calculated_sanksi, calculated_denda = \
            calculate_duration_and_penalties(jam_keluar_from_izin, jam_kembali_from_izin)

    db_dataTelat = models.DataTelat(
        izin_no=dataTelat.izin_no,
        user_uid=dataTelat.user_uid,
        by=None,
        keterangan=None,
        sanksi=calculated_sanksi,
        denda=calculated_denda,
        status="Pending"
    )
    db.add(db_dataTelat)
    db.commit()
    db.refresh(db_dataTelat)
    return db_dataTelat

def update_dataTelat(db: Session, dataTelat_no: int, dataTelat_update: schemas.DataTelatUpdate, current_user_uid: str = None):
    logger.info(f"Mencoba memperbarui DataTelat No: {dataTelat_no} dengan data: {dataTelat_update.model_dump()}")

    db_dataTelat = db.query(models.DataTelat).filter(models.DataTelat.no == dataTelat_no).first()
    if not db_dataTelat:
        logger.warning(f"Data Telat dengan nomor {dataTelat_no} tidak ditemukan.")
        return None

    logger.info(f"DataTelat sebelum update: Status='{db_dataTelat.status}', Keterangan='{db_dataTelat.keterangan}', By='{db_dataTelat.by}', Jam='{db_dataTelat.jam}'")

    update_data = dataTelat_update.model_dump(exclude_unset=True)

    # Simpan status lama untuk perbandingan
    old_status = db_dataTelat.status

    # Tangani logika untuk 'by'
    if "status" in update_data and update_data["status"] != old_status and current_user_uid:
        db_dataTelat.by = current_user_uid
        logger.info(f"Status berubah dari '{old_status}' ke '{update_data['status']}', mengatur 'by' menjadi: {db_dataTelat.by}")

    # --- PERBAIKAN PENTING UNTUK 'JAM' ---
    new_status = update_data.get("status")
    current_time_gmt7_str = get_local_datetime_gmt7(datetime.utcnow()).strftime("%H:%M:%S")

    if "jam" not in update_data or (update_data.get("jam") is None and new_status != old_status):
        db_dataTelat.jam = current_time_gmt7_str
        logger.info(f"Mengatur 'jam' ke waktu saat ini '{db_dataTelat.jam}' karena tidak di-set secara eksplisit atau status berubah.")
    elif "jam" in update_data and update_data["jam"] is not None:
        db_dataTelat.jam = update_data["jam"]
        logger.info(f"Mengatur 'jam' dari payload update: '{db_dataTelat.jam}'")
    else:
        db_dataTelat.jam = current_time_gmt7_str
        logger.info(f"Payload 'jam' dikirim sebagai null/kosong, memaksa 'jam' ke waktu saat ini: '{db_dataTelat.jam}'")

    # --- LOGIKA PENTING UNTUK 'KETERANGAN' DAN 'STATUS' ---
    new_keterangan = update_data.get("keterangan")

    if new_status:
        db_dataTelat.status = new_status
        logger.info(f"Status DataTelat diatur ke: '{db_dataTelat.status}'")

        if new_status == "Done":
            if new_keterangan is None or new_keterangan.strip() == "":
                db_dataTelat.keterangan = "Done Sanksi"
            else:
                db_dataTelat.keterangan = new_keterangan
        elif new_status in ["Izin", "Kendala"]:
            if new_keterangan is None or new_keterangan.strip() == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Keterangan wajib diisi jika status '{new_status}'."
                )
            else:
                db_dataTelat.keterangan = new_keterangan
        else:
            if "keterangan" in update_data:
                db_dataTelat.keterangan = new_keterangan
            else:
                db_dataTelat.keterangan = None
                logger.info(f"Status diatur ke '{new_status}', keterangan tidak di-set di payload, mengosongkan keterangan.")

    else:
        if "keterangan" in update_data:
            db_dataTelat.keterangan = new_keterangan
            logger.info(f"Keterangan diupdate tanpa perubahan status: '{db_dataTelat.keterangan}'")

    # Perbarui field lain yang spesifik dari payload dataTelat_update
    for key, value in update_data.items():
        if key not in ["by", "jam", "keterangan", "status"]:
            setattr(db_dataTelat, key, value)
            logger.debug(f"Mengatur {key} menjadi: {getattr(db_dataTelat, key)}")

    # Jika sanksi/denda tidak secara eksplisit diupdate, kita bisa menghitung ulang
    if "sanksi" not in update_data and "denda" not in update_data:
        db.refresh(db_dataTelat, attribute_names=['izin'])
        if db_dataTelat.izin and db_dataTelat.izin.jamKeluar and db_dataTelat.izin.jamKembali:
            _, calculated_sanksi, calculated_denda = \
                calculate_duration_and_penalties(db_dataTelat.izin.jamKeluar, db_dataTelat.izin.jamKembali)
            db_dataTelat.sanksi = calculated_sanksi
            db_dataTelat.denda = calculated_denda
            logger.info(f"Menghitung ulang sanksi/denda: Sanksi='{db_dataTelat.sanksi}', Denda='{db_dataTelat.denda}'")
        elif db_dataTelat.izin:
            db_dataTelat.sanksi = None
            db_dataTelat.denda = "0"
            logger.info("Izin ditemukan tetapi jamKeluar/jamKembali tidak ada, mengatur sanksi/denda ke None/0.")

    try:
        db.add(db_dataTelat)
        db.commit()
        db.refresh(db_dataTelat)
        logger.info(f"DataTelat No: {dataTelat_no} berhasil di-commit ke database. Status terbaru: '{db_dataTelat.status}', Jam terbaru: '{db_dataTelat.jam}'")
    except Exception as e:
        db.rollback()
        logger.error(f"Gagal melakukan commit perubahan untuk DataTelat No: {dataTelat_no}. Error: {e}", exc_info=True)
        raise

    return db_dataTelat

def delete_dataTelat(db: Session, dataTelat_no: int):
    db_dataTelat = db.query(models.DataTelat).filter(models.DataTelat.no == dataTelat_no).first()
    if db_dataTelat:
        db.delete(db_dataTelat)
        db.commit()
        return True
    return False

def delete_data_telat_by_izin_no(db: Session, izin_no: int) -> bool:
    """
    Menghapus entri DataTelat berdasarkan izin_no.
    Mengembalikan True jika ditemukan dan dihapus, False jika tidak ditemukan.
    """
    db_dataTelat = db.query(models.DataTelat).filter(models.DataTelat.izin_no == izin_no).first()
    if db_dataTelat:
        logger.info(f"Menghapus DataTelat terkait dengan Izin No: {izin_no}")
        db.delete(db_dataTelat)
        db.commit()
        return True
    logger.info(f"Tidak ada DataTelat ditemukan untuk Izin No: {izin_no}")
    return False

# --- FUNGSI TRANSFER DATA YANG BARU ---
def transfer_old_data_telat_to_archive(db: Session):
    try:
        # Dapatkan tahun saat ini di zona waktu GMT+7
        current_year_gmt7 = datetime.now(GMT7_TIMEZONE).year

        logger.info(f"Memulai proses pemindahan data telat lama. Data dengan tahun '{current_year_gmt7}' akan dipertahankan.")

        # Ambil semua data telat dan muat relasi 'izin' dan 'user' agar bisa diakses
        # Filter data yang izinnya bukan di tahun berjalan
        # Lakukan joinedload pada 'izin' dan 'user' agar data relasional siap saat iterasi
        old_datatelat_entries: List[models.DataTelat] = db.query(models.DataTelat)\
            .join(Izin, models.DataTelat.izin_no == Izin.no)\
            .filter(extract('year', Izin.tanggal) != current_year_gmt7)\
            .options(joinedload(models.DataTelat.izin), joinedload(models.DataTelat.user), joinedload(models.DataTelat.approved_by))\
            .all()

        if not old_datatelat_entries:
            logger.info("Tidak ada data telat lama yang ditemukan untuk diarsipkan (kecuali data tahun ini).")
            return

        datatelat_by_year = {}
        for datatelat_entry in old_datatelat_entries:
            # Pastikan izin terkait ada dan memiliki tanggal sebelum mencoba mengakses tahun
            if datatelat_entry.izin and datatelat_entry.izin.tanggal:
                year = datatelat_entry.izin.tanggal.year
                if year not in datatelat_by_year:
                    datatelat_by_year[year] = []
                datatelat_by_year[year].append(datatelat_entry)
            else:
                logger.warning(f"Data Telat No {datatelat_entry.no} tidak memiliki data izin atau tanggal izin yang valid, melewati pengarsipan.")


        for year, datatelat_to_transfer in datatelat_by_year.items():
            archive_table_name = f"dataTelat_{year}"
            DynamicDataTelatModel = models.DataTelat.create_dynamic_table_model(archive_table_name)

            archive_table_obj = DynamicDataTelatModel.__table__
            if not archive_table_obj.exists(db.bind):
                archive_table_obj.create(db.bind)
                logger.info(f"Tabel arsip '{archive_table_name}' berhasil dibuat.")

            transferred_count = 0
            for datatelat_entry in datatelat_to_transfer:
                try:
                    new_archive_datatelat_data = {}
                    # Dapatkan semua kolom dari model DataTelat asli
                    for column in models.DataTelat.__table__.columns:
                        # Kita tidak perlu menyalin primary key (no) karena akan dibuat otomatis di tabel baru
                        if column.name == 'no':
                            continue

                        value = getattr(datatelat_entry, column.name)

                        # Konversi datetime menjadi UTC-aware jika belum
                        if isinstance(value, datetime) and value is not None and value.tzinfo is None:
                            new_archive_datatelat_data[column.name] = value.replace(tzinfo=timezone.utc)
                        else:
                            new_archive_datatelat_data[column.name] = value

                    # Buat instance model arsip dan tambahkan ke sesi
                    new_archive_datatelat = DynamicDataTelatModel(**new_archive_datatelat_data)
                    db.add(new_archive_datatelat)

                    # Hapus data dari tabel utama
                    db.delete(datatelat_entry)
                    transferred_count += 1
                    logger.debug(f"Memindahkan DataTelat No {datatelat_entry.no} (Izin No {datatelat_entry.izin_no}) ke {archive_table_name}")

                except Exception as e:
                    db.rollback()
                    logger.error(f"Gagal memindahkan DataTelat No {datatelat_entry.no} ke {archive_table_name}: {e}", exc_info=True)
                    # Lanjutkan ke entri berikutnya meskipun ada kesalahan pada satu entri

            db.commit() # Commit setiap batch per tahun
            logger.info(f"Berhasil memindahkan {transferred_count} data telat ke '{archive_table_name}'.")

    except Exception as e:
        db.rollback()
        logger.error(f"Kesalahan umum saat memindahkan data telat: {e}", exc_info=True)
        raise