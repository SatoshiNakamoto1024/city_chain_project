# user_manager/utils/storage_checker.py

import shutil
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def check_ios():
    logger.info("iOSデバイス：ストレージチェック省略（仮定OK）")
    return True

def check_android():
    logger.info("Androidデバイス：ストレージチェック省略（仮定OK）")
    return True

def check_pc():
    try:
        total, used, free = shutil.disk_usage("/")
        logger.info(f"PC空き容量: {free / (1024 * 1024)} MB")
        return free >= 100 * 1024 * 1024
    except Exception as e:
        logger.error(f"PCストレージ確認エラー: {e}")
        return False

def check_game():
    logger.info("ゲーム機：仮定でストレージOK")
    return True

def check_tv():
    logger.info("スマートTV：仮定でストレージOK")
    return True

def check_car():
    logger.info("カーナビ端末：仮定でストレージOK")
    return True

def check_iot():
    try:
        total, used, free = shutil.disk_usage("/")
        logger.info(f"IoT空き容量: {free / (1024 * 1024)} MB")
        return free >= 100 * 1024 * 1024
    except Exception as e:
        logger.error(f"IoTストレージ確認エラー: {e}")
        return False

def check_unknown():
    logger.warning("不明な端末タイプ：ストレージNG扱い")
    return False

def check_storage(platform_type: str) -> bool:
    platform_type = platform_type.lower()
    dispatch_table = {
        "ios": check_ios,
        "android": check_android,
        "pc": check_pc,
        "game": check_game,
        "tv": check_tv,
        "car": check_car,
        "iot": check_iot,
        "unknown": check_unknown
    }
    checker = dispatch_table.get(platform_type, check_unknown)
    return checker()
