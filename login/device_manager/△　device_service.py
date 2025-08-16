# device_manager/device_service.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
import logging
from datetime import datetime
from device_manager.device_db import (
    save_device, get_devices_by_user, delete_device,
    get_primary_session, delete_primary_session
)
from device_manager.device_model import Device
from device_manager.concurrency_policy import handle_concurrency_if_needed
from device_manager.concurrency_policy import should_reject_login

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

    # 🔍 1. 既存の端末（DevicesTable + UsersTable）を取得
    devices = get_devices_by_user(user_uuid)
    primary = get_primary_session(user_uuid)  # UsersTable にある最初の端末（session_id）

    already_logged_in = []

    if primary:
        already_logged_in.append(f"[Primary] {primary.get('session_id', '')}")

    for d in devices:
        if d.is_active:
            already_logged_in.append(d.device_id)

    if already_logged_in and not force:
        raise Exception(f"他の端末がログイン中です: {already_logged_in}")

    # 🔨 2. force=True の場合、既存端末を強制ログアウト（DevicesTable + UsersTable）
    if force:
        if primary:
            delete_primary_session(user_uuid, primary["session_id"])
            logger.info("強制ログアウト: UsersTable session_id=%s", primary["session_id"])

        for d in devices:
            if d.is_active:
                delete_device(user_uuid, d.device_id)
                logger.info("強制ログアウト: DevicesTable device_id=%s", d.device_id)

    # ✅ 3. 新端末を登録
    device = Device(
        uuid=user_uuid,
        device_id=device_id,
        device_name=device_name,
        registered_at=now,
        is_active=True,
        login_at = now
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
    特定端末の登録を解除
    """
    delete_device(user_uuid, device_id)
    logger.info("端末 unbind 完了: %s", device_id)

def force_logout_other_devices(user_uuid: str, new_device_id: str) -> dict:
    """
    concurrency_policy: ユーザーが新端末を追加した際に、
    古い端末を強制ログアウト(=inactive化 or session終了)する。
    """
    from device_manager.concurrency_policy import force_logout_other_devices_impl
    return force_logout_other_devices_impl(user_uuid, new_device_id)
