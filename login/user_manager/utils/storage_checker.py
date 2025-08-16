# File: login/user_manager/utils/storage_checker.py

import shutil
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MIN_FREE_SPACE_BYTES = 100 * 1024 * 1024  # 100MB

def check_storage(platform_type: str) -> bool:
    """
    プラットフォーム種別に応じて100MB以上あるかを判定する。
    """
    pt = platform_type.lower()

    if pt in ["pc", "iot"]:
        # サーバー同一マシンの空き容量を直接チェック
        try:
            total, used, free = shutil.disk_usage("/")
            logger.info(f"[{pt}] free = {free} bytes")
            return free >= MIN_FREE_SPACE_BYTES
        except Exception as e:
            logger.error(f"[{pt}] Disk check error: {e}")
            return False
    elif pt in ["android", "ios", "game", "car", "tv"]:
        # 本来はクライアントから送られた client_free_space を使うが、
        # このサンプルでは "仮OK" として True を返す例
        logger.info(f"[{pt}] skipping local check; assume True.")
        return True
    else:
        logger.warning(f"[{pt}] unknown platform -> return False.")
        return False
    
def check_server_disk_usage(path="/"):
    """
    サーバー自身のpath(デフォルトは"/")について、
    空き容量が 100MB (MIN_FREE_SPACE_BYTES) 以上あるかを確認する。
    
    例: PCサーバーやIoTデバイスとサーバーアプリが同じマシンにある状況なら
        この関数で直接ディスク空き容量を調べて判断する。
    """
    try:
        total, used, free = shutil.disk_usage(path)
        logger.info(f"[Server] Checking disk usage at {path}: free={free} bytes")
        return free >= MIN_FREE_SPACE_BYTES
    except Exception as e:
        logger.error(f"[Server] Disk usage check failed: {e}")
        return False
