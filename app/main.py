# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.core.firebase import initialize_firebase_admin
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
import logging
from app.users import router as users_router
from app.roles import router as roles_router
from app.dataizin import router as dataizin_router
from app.dataizin import crud as crud_data_izin
from app.datatelat import router as datatelat_router
from app.datatelat import crud as crud_data_telat
from app.autentikasi import router as auth_router
from app.shift import router as shift_router

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Konfigurasi CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://adminreachpython.web.app",
    "https://adminpython.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tambahkan endpoint ini untuk tampilan awal
@app.get("/")
async def read_root():
    """
    Endpoint root untuk API Admin Panel.
    Mengembalikan pesan selamat datang dan informasi dasar API.
    """
    return {
        "message": "Selamat datang di Admin Panel API!",
        "project_name": settings.PROJECT_NAME,
        "health_check": "API is running successfully."
    }

# Sertakan router API setelah middleware CORS
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(roles_router.router)
app.include_router(dataizin_router.router)
app.include_router(datatelat_router.router)
app.include_router(shift_router.router)

# Inisialisasi scheduler
scheduler = AsyncIOScheduler()

# Fungsi terpisah untuk transfer data izin
def scheduled_transfer_izin_task():
    logger.info("Memicu tugas transfer data izin terjadwal...")
    db_session: Session = next(get_db())
    try:
        crud_data_izin.transfer_old_data_izin_to_archive(db_session)
    except Exception as e:
        logger.error(f"Kesalahan dalam tugas transfer data izin terjadwal: {e}", exc_info=True)
    finally:
        db_session.close()

# Fungsi terpisah untuk transfer data telat
def scheduled_transfer_telat_task():
    logger.info("Memicu tugas transfer data telat terjadwal...")
    db_session: Session = next(get_db())
    try:
        crud_data_telat.transfer_old_data_telat_to_archive(db_session)
    except Exception as e:
        logger.error(f"Kesalahan dalam tugas transfer data telat terjadwal: {e}", exc_info=True)
    finally:
        db_session.close()

@app.on_event("startup")
async def startup_event():
    logger.info("Membuat tabel database jika belum ada...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tabel database berhasil dibuat atau sudah ada.")

    # Inisialisasi Firebase Admin SDK di startup
    initialize_firebase_admin()
    
    # Menjadwalkan transfer data izin setiap hari jam 1 pagi
    scheduler.add_job(
        scheduled_transfer_izin_task,
        CronTrigger(hour=1, minute=0), # Setiap hari pada jam 1 pagi
        id='transfer_izin_data_job',
        replace_existing=True
    )
    logger.info("Tugas transfer data izin terjadwal setiap hari jam 1 pagi.")

    # Menjadwalkan transfer data telat setiap pergantian tahun
    scheduler.add_job(
        scheduled_transfer_telat_task,
        CronTrigger(month=1, day=1, hour=0, minute=0), # Setiap 1 Januari jam 00:00
        id='transfer_telat_data_job',
        replace_existing=True
    )
    logger.info("Tugas transfer data telat terjadwal setiap pergantian tahun.")

    scheduler.start()
    logger.info("Scheduler APSScheduler dimulai.")