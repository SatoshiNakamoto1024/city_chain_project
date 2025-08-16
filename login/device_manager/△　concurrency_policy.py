# device_manager/concurrency_policy.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging
from device_manager.device_db import get_devices_by_user, delete_device
from device_manager.device_db import get_active_devices_count

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 同時利用台数（テストでは1台まで保持）
MAX_CONCURRENT_DEVICES = 1

def should_reject_login(user_uuid: str) -> bool:
    """
    新規ログインを拒否すべきかどうかを判定
    """
    if MAX_CONCURRENT_DEVICES <= 0:
        return False  # 無制限

    active_count = get_active_devices_count(user_uuid)
    return active_count >= MAX_CONCURRENT_DEVICES

def handle_concurrency_if_needed(user_uuid: str, new_device_id: str):
    """
    新端末が登録された際に、同時利用端末数を超えていれば古い端末を排除する or 強制ログアウト。
    """
    if MAX_CONCURRENT_DEVICES <= 0:
        return  # 0なら無制限扱いなど

    devices = get_devices_by_user(user_uuid)
    if len(devices) > MAX_CONCURRENT_DEVICES:
        # シンプルに一番古い端末を削除する例
        devices_sorted = sorted(devices, key=lambda d: d.registered_at)
        # keep the newest 1
        to_remove = devices_sorted[:-1]  # newestだけ残す
        for dev in to_remove:
            logger.info("同時利用数超過: 古い端末を削除 => device_id=%s", dev.device_id)
            delete_device(user_uuid, dev.device_id)

def force_logout_other_devices_impl(user_uuid: str, new_device_id: str) -> dict:
    devices = get_devices_by_user(user_uuid)
    if not devices:
        return {"message": "no devices found"}

    # もっとも login_at が早いものを残す（= 先にログインしていたもの）
    devices_sorted = sorted(devices, key=lambda d: d.login_at)
    keep_device = devices_sorted[0]

    logged_out = []

    for dev in devices:
        if dev.device_id != keep_device.device_id:
            delete_device(user_uuid, dev.device_id)
            logged_out.append(dev.device_id)

    return {
        "message": f"keep device: {keep_device.device_id}",
        "logged_out": logged_out
    }
