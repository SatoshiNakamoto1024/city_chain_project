# File: login/user_manager/utils/platform_utils.py

def detect_platform_from_headers(headers):
    """
    User-Agent や X-Device-Type ヘッダから端末種類を判定。
    対象: pc, ios, android, game, iot, car, tv, unknown
    """
    ua = headers.get("User-Agent", "").lower()
    device_hint = headers.get("X-Device-Type", "").lower()

    if device_hint:
        return device_hint

    if "android" in ua:
        return "android"
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        return "ios"
    elif "windows" in ua or "macintosh" in ua or "linux" in ua:
        return "pc"
    elif "playstation" in ua or "xbox" in ua or "nintendo" in ua:
        return "game"
    elif "smart-tv" in ua or "hbbtv" in ua or "tizen" in ua:
        return "tv"
    elif "raspberry" in ua or "iot" in ua:
        return "iot"
    elif "carplay" in ua or "ivi" in ua or "car" in ua:
        return "car"
    else:
        return "unknown"
