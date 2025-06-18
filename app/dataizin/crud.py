# app/dataizin/crud.py (Revisi dengan hapus 'jabatan')

from sqlalchemy.orm import Session, joinedload
from app.dataizin import models, schemas
from datetime import datetime, timedelta, date, timezone
from typing import Optional, List # Tambahkan List
import enum # Tambahkan enum
import logging # Tambahkan logging

# Inisialisasi logger
logger = logging.getLogger(__name__)
# Contoh konfigurasi dasar (sesuaikan dengan setup logging aplikasi Anda)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Definisikan offset untuk GMT+7
GMT7_OFFSET = timedelta(hours=7)
GMT7_TIMEZONE = timezone(GMT7_OFFSET)

# --- Tambahan: Fungsi untuk mengonversi UTC ke GMT+7 ---
def get_local_datetime_gmt7(dt_utc: datetime) -> datetime:
    """Mengonversi datetime UTC menjadi datetime dengan zona waktu GMT+7."""
    if dt_utc.tzinfo is None:
        # Jika datetime naive, asumsikan itu UTC dan buat aware
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    
    # Konversi ke zona waktu GMT+7
    return dt_utc.astimezone(GMT7_TIMEZONE)

# --- Tambahan: Fungsi untuk memastikan datetime adalah UTC aware ---
def convert_to_utc_aware(dt: datetime) -> datetime:
    """Mengonversi datetime menjadi UTC aware jika belum."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

# --- Fungsi dummy untuk delete_data_telat_by_izin_no (Anda perlu mengimplementasikannya) ---
def delete_data_telat_by_izin_no(db: Session, izin_no: int):
    """
    Fungsi placeholder untuk menghapus data terkait 'data_telat' berdasarkan nomor izin.
    Anda perlu mengimplementasikan logika ini berdasarkan model 'data_telat' Anda.
    """
    logger.info(f"Menghapus data terkait 'data_telat' untuk izin_no: {izin_no} (placeholder)")
    # Contoh: db.query(models.DataTelat).filter(models.DataTelat.izin_no == izin_no).delete()
    # db.commit()

# --- Fungsi yang sudah ada (tanpa perubahan besar, kecuali yang dimodifikasi) ---
def get_izin(db: Session, izin_no: int):
    return db.query(models.Izin).options(joinedload(models.Izin.user)).filter(models.Izin.no == izin_no).first()

def get_izins(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Izin).options(joinedload(models.Izin.user)).offset(skip).limit(limit).all()

def create_izin(db: Session, izin: schemas.IzinCreate):
    # Pastikan jamKeluar adalah UTC saat disimpan
    if izin.jamKeluar.tzinfo is None:
        izin.jamKeluar = izin.jamKeluar.replace(tzinfo=timezone.utc)

    db_dataIzin = models.Izin(
        user_uid=izin.user_uid,
        tanggal=izin.tanggal, 
        jamKeluar=izin.jamKeluar,
        ipKeluar=izin.ipKeluar,
        status="Pending",
        durasi=None
    )
    db.add(db_dataIzin)
    db.commit()
    db.refresh(db_dataIzin)
    return db_dataIzin

def update_izin_kembali(db: Session, izin_no: int, jamKembali: datetime, ipKembali: str):
    db_dataIzin = db.query(models.Izin).filter(models.Izin.no == izin_no).first()
    if not db_dataIzin:
        return None

    # Pastikan jamKembali adalah UTC saat disimpan jika belum aware
    if jamKembali.tzinfo is None:
        jamKembali = jamKembali.replace(tzinfo=timezone.utc)

    db_dataIzin.jamKembali = jamKembali
    db_dataIzin.ipKembali = ipKembali

    if db_dataIzin.jamKeluar and db_dataIzin.jamKembali:
        jam_keluar_aware = db_dataIzin.jamKeluar if db_dataIzin.jamKeluar.tzinfo is not None else db_dataIzin.jamKeluar.replace(tzinfo=timezone.utc)
        jam_kembali_aware = db_dataIzin.jamKembali if db_dataIzin.jamKembali.tzinfo is not None else db_dataIzin.jamKembali.replace(tzinfo=timezone.utc)

        delta = jam_kembali_aware - jam_keluar_aware
        total_seconds = int(delta.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        duration_parts = []
        if hours > 0:
            duration_parts.append(f"{hours} Jam")
        if minutes > 0:
            duration_parts.append(f"{minutes} Menit")
        if seconds > 0:
            duration_parts.append(f"{seconds} Detik")

        if not duration_parts:
            db_dataIzin.durasi = "0 Detik"
        else:
            db_dataIzin.durasi = " ".join(duration_parts)

        if total_seconds > (15 * 60):
            db_dataIzin.status = "Lewat Waktu"
        else:
            db_dataIzin.status = "Tepat Waktu"
    else:
        db_dataIzin.status = "Pending"
        db_dataIzin.durasi = None

    db.add(db_dataIzin)
    db.commit()
    db.refresh(db_dataIzin)
    return db_dataIzin

def update_izin(db: Session, izin_no: int, izin_update: schemas.IzinUpdate):
    db_dataIzin = db.query(models.Izin).filter(models.Izin.no == izin_no).first()
    if not db_dataIzin:
        return None

    update_data = izin_update.model_dump(exclude_unset=True)

    if "user_uid" in update_data:
        db_dataIzin.user_uid = update_data["user_uid"]
    update_data.pop("user_uid", None)
    
    # HAPUS PENANGANAN JABATAN DARI UPDATE
    # Baris ini memastikan bahwa jika 'jabatan' ada di update_data, itu akan dihapus
    # sebelum iterasi dan menetapkan atribut.
    update_data.pop("jabatan", None) 
    
    for key, value in update_data.items():
        if key == "jamKeluar" and value and value.tzinfo is None: 
            setattr(db_dataIzin, key, value.replace(tzinfo=timezone.utc))
        elif key == "jamKembali" and value and value.tzinfo is None: 
            setattr(db_dataIzin, key, value.replace(tzinfo=timezone.utc))
        else:
            setattr(db_dataIzin, key, value)

    if db_dataIzin.jamKeluar and db_dataIzin.jamKembali:
        jam_keluar_aware = db_dataIzin.jamKeluar if db_dataIzin.jamKeluar.tzinfo is not None else db_dataIzin.jamKeluar.replace(tzinfo=timezone.utc)
        jam_kembali_aware = db_dataIzin.jamKembali if db_dataIzin.jamKembali.tzinfo is not None else db_dataIzin.jamKembali.replace(tzinfo=timezone.utc)

        delta = jam_kembali_aware - jam_keluar_aware
        total_seconds = int(delta.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        duration_parts = []
        if hours > 0:
            duration_parts.append(f"{hours} Jam")
        if minutes > 0:
            duration_parts.append(f"{minutes} Menit")
        if seconds > 0:
            duration_parts.append(f"{seconds} Detik")

        if not duration_parts:
            db_dataIzin.durasi = "0 Detik"
        else:
            db_dataIzin.durasi = " ".join(duration_parts)

        if total_seconds > (15 * 60):
            db_dataIzin.status = "Lewat Waktu"
        else:
            db_dataIzin.status = "Tepat Waktu"
    elif db_dataIzin.jamKeluar and not db_dataIzin.jamKembali:
        db_dataIzin.status = "Pending"
    elif not db_dataIzin.jamKeluar and not db_dataIzin.jamKembali:
        db_dataIzin.status = "Pending"
    else: 
        db_dataIzin.status = "Pending"

    db.add(db_dataIzin)
    db.commit()
    db.refresh(db_dataIzin)
    return db_dataIzin


def delete_izin(db: Session, izin_no: int):
    db_dataIzin = db.query(models.Izin).filter(models.Izin.no == izin_no).first()
    if db_dataIzin:
        db.delete(db_dataIzin)
        db.commit()
        return True
    return False

def get_izin_count_for_today(db: Session, user_uid: str) -> int:
    """
    Menghitung jumlah izin yang dibuat oleh user_uid pada tanggal lokal GMT+7 hari ini.
    Kita harus mengonversi tanggal izin yang tersimpan (UTC) ke GMT+7 untuk perbandingan.
    """
    now_utc = datetime.now(timezone.utc)
    today_gmt7 = get_local_datetime_gmt7(now_utc).date()

    # Mengambil awal dan akhir hari GMT+7 dalam UTC
    start_of_day_gmt7_aware = datetime.combine(today_gmt7, datetime.min.time()).replace(tzinfo=GMT7_TIMEZONE)
    end_of_day_gmt7_aware = datetime.combine(today_gmt7, datetime.max.time()).replace(tzinfo=GMT7_TIMEZONE)

    # Mengonversi kembali ke UTC untuk perbandingan di database
    start_of_day_utc = start_of_day_gmt7_aware.astimezone(timezone.utc)
    end_of_day_utc = end_of_day_gmt7_aware.astimezone(timezone.utc)

    count = db.query(models.Izin).filter(
        models.Izin.user_uid == user_uid,
        models.Izin.createOn >= start_of_day_utc,
        models.Izin.createOn <= end_of_day_utc
    ).count()
    return count

def get_pending_izin_by_user(db: Session, user_uid: str):
    """Mengambil izin yang statusnya 'Pending' untuk user tertentu."""
    return db.query(models.Izin).options(joinedload(models.Izin.user)).filter(
        models.Izin.user_uid == user_uid,
        models.Izin.status == "Pending"
    ).first()

def get_izin_history_by_user(db: Session, user_uid: str, tanggal: Optional[date] = None, skip: int = 0, limit: int = 100):
    """Mengambil riwayat izin untuk user tertentu, dengan opsi filter tanggal."""
    query = db.query(models.Izin).options(joinedload(models.Izin.user)).filter(
        models.Izin.user_uid == user_uid
    )
    if tanggal:
        # Mengonversi tanggal lokal input menjadi rentang UTC untuk query
        start_of_target_day_gmt7 = datetime.combine(tanggal, datetime.min.time()).replace(tzinfo=GMT7_TIMEZONE)
        end_of_target_day_gmt7 = datetime.combine(tanggal, datetime.max.time()).replace(tzinfo=GMT7_TIMEZONE)
        
        start_of_target_day_utc = start_of_target_day_gmt7.astimezone(timezone.utc)
        end_of_target_day_utc = end_of_target_day_gmt7.astimezone(timezone.utc)
        
        query = query.filter(
            models.Izin.createOn >= start_of_target_day_utc,
            models.Izin.createOn <= end_of_target_day_utc
        )
    
    query = query.order_by(models.Izin.tanggal.desc(), models.Izin.createOn.desc())
    
    return query.offset(skip).limit(limit).all()

def get_all_pending_izins(db: Session, skip: int = 0, limit: int = 100):
    """Mengambil semua izin yang statusnya 'Pending' dari semua user."""
    return db.query(models.Izin).options(joinedload(models.Izin.user)).filter(
        models.Izin.status == "Pending"
    ).offset(skip).limit(limit).all()

def get_all_izins_history(db: Session, tanggal: Optional[date] = None, skip: int = 0, limit: int = 100):
    """
    Mengambil semua riwayat izin dari semua user, dengan opsi filter tanggal.
    Filter tanggal bekerja berdasarkan tanggal lokal GMT+7 dari `createOn`.
    """
    query = db.query(models.Izin).options(joinedload(models.Izin.user))

    if tanggal:
        # Mengonversi tanggal lokal input menjadi rentang UTC untuk query
        start_of_target_day_gmt7 = datetime.combine(tanggal, datetime.min.time()).replace(tzinfo=GMT7_TIMEZONE)
        end_of_target_day_gmt7 = datetime.combine(tanggal, datetime.max.time()).replace(tzinfo=GMT7_TIMEZONE)
        
        start_of_target_day_utc = start_of_target_day_gmt7.astimezone(timezone.utc)
        end_of_target_day_utc = end_of_target_day_gmt7.astimezone(timezone.utc)
        
        query = query.filter(
            models.Izin.createOn >= start_of_target_day_utc,
            models.Izin.createOn <= end_of_target_day_utc
        )
    
    query = query.order_by(models.Izin.tanggal.desc(), models.Izin.createOn.desc())
    
    return query.offset(skip).limit(limit).all()

def get_izin_by_no(db: Session, izin_no: int):
    """
    Mengambil objek Izin dari database berdasarkan nomor izinnya.
    """
    return db.query(models.Izin).options(joinedload(models.Izin.user)).filter(models.Izin.no == izin_no).first()

def get_oldest_data_izin_date(db: Session) -> Optional[date]: 
    result = db.query(models.Izin.tanggal).order_by(models.Izin.tanggal.asc()).first() 
    return result[0] if result else None 

### FUNGSI TRANSFER DATA YANG DIREVISI

def transfer_old_data_izin_to_archive(db: Session): 
    try: 
        # Dapatkan tanggal hari ini di zona waktu GMT+7 
        now_utc = datetime.now(timezone.utc)
        today_gmt7 = get_local_datetime_gmt7(now_utc).date()

        logger.info(f"Memulai proses pemindahan data izin lama. Data dengan tanggal '{today_gmt7}' akan dipertahankan.") 

        # Filter semua data yang BUKAN tanggal hari ini 
        old_izins: List[models.Izin] = db.query(models.Izin).filter( 
            models.Izin.tanggal != today_gmt7
        ).all() 

        if not old_izins: 
            logger.info("Tidak ada data izin lama yang ditemukan untuk diarsipkan (kecuali data hari ini).") 
            return 

        izins_by_year = {} 
        for izin in old_izins: 
            year = izin.tanggal.year 
            # Semua data yang bukan hari ini akan dipertimbangkan untuk diarsipkan berdasarkan tahunnya 
            if year not in izins_by_year: 
                izins_by_year[year] = [] 
            izins_by_year[year].append(izin) 

        for year, izins_to_transfer in izins_by_year.items(): 
            archive_table_name = f"dataIzin_{year}" 
            # Pastikan models.Izin.create_dynamic_table_model tersedia dan berfungsi dengan baik
            DynamicDataIzinModel = models.Izin.create_dynamic_table_model(archive_table_name) 

            archive_table_obj = DynamicDataIzinModel.__table__ 
            if not archive_table_obj.exists(db.bind): 
                archive_table_obj.create(db.bind) 
                logger.info(f"Tabel arsip '{archive_table_name}' berhasil dibuat.") 

            transferred_count = 0 
            for izin in izins_to_transfer: 
                try: 
                    # Memastikan izin.no adalah integer sebelum memanggil delete_data_telat_by_izin_no
                    if isinstance(izin.no, int): 
                        delete_data_telat_by_izin_no(db, izin_no=izin.no) 
                    else: 
                        logger.warning(f"Izin No '{izin.no}' bukan integer, tidak dapat menghapus data telat terkait.") 

                    new_archive_izin_data = {} 
                    for column in models.Izin.__table__.columns:  
                        if column.name == 'no':  
                            continue  
                        
                        value = getattr(izin, column.name) 
                        if isinstance(value, datetime) and value is not None: 
                            new_archive_izin_data[column.name] = convert_to_utc_aware(value) 
                        elif isinstance(value, enum.Enum):  
                            new_archive_izin_data[column.name] = value.value 
                        else: 
                            new_archive_izin_data[column.name] = value 
                        
                    new_archive_izin = DynamicDataIzinModel(**new_archive_izin_data) 

                    db.add(new_archive_izin) 
                    db.delete(izin)  
                    transferred_count += 1 
                    logger.debug(f"Memindahkan DataIzin No {izin.no} ke {archive_table_name}")  
                except Exception as e: 
                    # Rollback untuk transaksi internal jika ada masalah dengan satu izin
                    logger.error(f"Gagal memindahkan DataIzin No {izin.no} ke {archive_table_name}: {e}", exc_info=True) 

            # Commit setelah mencoba memindahkan semua izin untuk tahun tertentu
            db.commit() 
            logger.info(f"Berhasil memindahkan {transferred_count} data izin ke '{archive_table_name}'.") 

    except Exception as e: 
        # Rollback untuk seluruh proses jika ada kesalahan umum
        db.rollback() 
        logger.error(f"Kesalahan umum saat memindahkan data izin: {e}", exc_info=True) 
        raise # Reraise exception setelah logging dan rollback