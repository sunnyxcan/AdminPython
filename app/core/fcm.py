# app/core/fcm.py

import firebase_admin
from firebase_admin import credentials, messaging
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Asumsi firebase_admin sudah diinisialisasi di app/main.py
# Jika belum, pastikan Anda memanggil initialize_firebase_admin()
# yang memuat kredensial Anda.

async def send_fcm_notification(
    device_tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
    image_url: Optional[str] = None
):
    """
    Mengirim notifikasi FCM ke daftar token perangkat yang diberikan.
    """
    if not firebase_admin._apps:
        logger.error("Firebase Admin SDK belum diinisialisasi. Tidak dapat mengirim notifikasi.")
        return

    if not device_tokens:
        logger.info("Tidak ada token perangkat yang diberikan, tidak ada notifikasi yang dikirim.")
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
            image=image_url # Opsional: URL gambar notifikasi
        ),
        data=data, # Opsional: Data kustom untuk aplikasi
        tokens=device_tokens,
    )

    try:
        response = await messaging.send_multicast_async(message)
        logger.info(f"Berhasil mengirim {response.success_count} pesan, gagal {response.failure_count}.")
        if response.failure_count > 0:
            for error in response.responses:
                if error.exception:
                    logger.warning(f"Gagal mengirim pesan: {error.exception}")
        return response
    except Exception as e:
        logger.error(f"Kesalahan saat mengirim notifikasi FCM: {e}", exc_info=True)
        return None

async def send_fcm_notification_to_all_users(db_session, title: str, body: str, data: Optional[Dict[str, str]] = None):
    """
    Mengambil semua token FCM dari database dan mengirim notifikasi ke semua.
    """
    from app.users.crud import get_users_fcm_tokens # Import di dalam fungsi untuk menghindari circular import
    all_fcm_tokens = get_users_fcm_tokens(db_session)
    if not all_fcm_tokens:
        logger.info("Tidak ada token FCM yang terdaftar untuk mengirim notifikasi ke semua pengguna.")
        return

    await send_fcm_notification(
        device_tokens=all_fcm_tokens,
        title=title,
        body=body,
        data=data
    )

async def send_fcm_notification_to_single_user(db_session, user_uid: str, title: str, body: str, data: Optional[Dict[str, str]] = None):
    """
    Mengambil token FCM untuk user tertentu dan mengirim notifikasi.
    """
    from app.users.crud import get_fcm_token_by_user_uid # Import di dalam fungsi untuk menghindari circular import
    fcm_token = get_fcm_token_by_user_uid(db_session, user_uid)
    if not fcm_token:
        logger.info(f"Tidak ada token FCM yang terdaftar untuk user_uid: {user_uid}")
        return

    await send_fcm_notification(
        device_tokens=[fcm_token],
        title=title,
        body=body,
        data=data
    )