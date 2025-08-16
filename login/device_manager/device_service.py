import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
import logging
from datetime import datetime

from device_manager.device_db import (
    save_device,
    get_devices_by_user,
    delete_device,
    get_primary_session,
    delete_primary_session
)
from device_manager.device_model import Device

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def register_device_for_user(user_uuid: str, qr_code: str, device_name: str, force: bool = False) -> dict:
    """
    新端末をユーザーに紐付ける。
    - force=False の場合、他端末がログイン中なら登録拒否。
    - force=True の場合、他端末を強制ログアウト。
    """
    device_id = "dev-" + uuid.uuid4().hex[:6]
    now = datetime.utcnow().isoformat()

    # 既存の端末情報を取得
    devices = get_devices_by_user(user_uuid)
    primary = get_primary_session(user_uuid)

    # ログイン中の端末があれば拒否
    logged_in = []
    if primary:
        logged_in.append(f"[Primary] {primary.get('session_id', '')}")
    for d in devices:
        if d.is_active:
            logged_in.append(d.device_id)

    if logged_in and not force:
        raise Exception(f"他の端末がログイン中です: {logged_in}")

    # force=True なら既存端末を強制ログアウト
    if force:
        if primary:
            delete_primary_session(user_uuid, primary["session_id"])
            logger.info("強制ログアウト: UsersTable session_id=%s", primary["session_id"])
        for d in devices:
            if d.is_active:
                delete_device(user_uuid, d.device_id)
                logger.info("強制ログアウト: DevicesTable device_id=%s", d.device_id)

    # 新端末を登録
    device = Device(
        uuid          = user_uuid,
        device_id     = device_id,
        device_name   = device_name,
        registered_at = now,
        is_active     = True,
        login_at      = now
    )
    save_device(device)
    return device.to_dict()

def list_devices_for_user(user_uuid: str) -> list:
    """
    ユーザーの登録端末一覧を返す
    """
    devices = get_devices_by_user(user_uuid)
    return [d.to_dict() for d in devices]

def unbind_device(user_uuid: str, device_id: str):
    """
    特定端末の登録解除
    """
    delete_device(user_uuid, device_id)
    logger.info("端末 unbind 完了: %s", device_id)

def force_logout_other_devices(user_uuid: str, new_device_id: str) -> dict:
    """
    新端末追加時に、他の端末を強制ログアウト
    """
    from device_manager.concurrency_policy import force_logout_other_devices_impl
    return force_logout_other_devices_impl(user_uuid, new_device_id)
