# D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python\rvh_faultset\geohash.py
"""
Pure-Python Geohash 実装

precision に応じて緯度経度をビット分割し、
Base32 文字列を返します。
"""

__base32 = "0123456789bcdefghjkmnpqrstuvwxyz"

def encode(lat: float, lon: float, precision: int = 6) -> str:
    """
    Geohash エンコード

    Args:
        lat: 緯度 [-90.0, 90.0]
        lon: 経度 [-180.0, 180.0]
        precision: 出力文字数 (1〜12)

    Returns:
        Geohash 文字列
    """
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    geohash = []
    bit = 0
    ch = 0
    even = True

    while len(geohash) < precision:
        if even:
            mid = (lon_interval[0] + lon_interval[1]) / 2
            if lon > mid:
                ch |= 1 << (4 - bit)
                lon_interval[0] = mid
            else:
                lon_interval[1] = mid
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2
            if lat > mid:
                ch |= 1 << (4 - bit)
                lat_interval[0] = mid
            else:
                lat_interval[1] = mid

        even = not even
        if bit < 4:
            bit += 1
        else:
            geohash.append(__base32[ch])
            bit = 0
            ch = 0

    return "".join(geohash)


def geohash_cluster(nodes: list[dict], precision: int) -> list[list[dict]]:
    """
    nodes: {"id","lat","lon","latency"} 辞書のリスト
    precision: geohash 文字長 (1〜12)
    戻り値: 同じプレフィックスでまとめたノード群のリスト
    """
    if precision < 1 or precision > 12:
        raise ValueError("precision must be between 1 and 12")
    buckets: dict[str, list[dict]] = {}
    for n in nodes:
        code = encode(n["lat"], n["lon"], precision)
        buckets.setdefault(code, []).append(n)
    return list(buckets.values())
