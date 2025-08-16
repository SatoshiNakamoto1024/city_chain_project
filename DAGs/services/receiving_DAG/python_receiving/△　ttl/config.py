"""TTL 設定を一元管理"""
from dataclasses import dataclass

@dataclass
class TTLConfig:
    # 秒数
    FRESH_TX_TTL   : float = 60.0     # 1 分
    POH_REQ_TTL    : float = 30.0
    POH_ACK_TTL    : float = 6 * 3600 # 6 時間 (保存キャッシュ)
    REPAIR_REQ_TTL : float = 15.0
    REPAIR_ACK_TTL : float = 60.0

    GC_INTERVAL    : float = 5.0      # 5 秒毎にスキャン
    GC_BATCH       : int   = 500      # 1 batch で削除する上限