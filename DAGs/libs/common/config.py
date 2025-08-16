# D:\city_chain_project\network\sending_DAGs\python_sending\common\config.py

"""
config.py

バッチインターバルの可変設定やErasure Codingの冗長度設定など、
本番想定での追加要素を含めた共通設定。
"""

import hashlib
import random
import os
import time

# -------------------------
# 可変バッチ制御パラメータ
# -------------------------
# バッチの最小間隔と最大間隔（秒）
MIN_BATCH_INTERVAL = 0.5
MAX_BATCH_INTERVAL = 5.0

# 1回のバッチでまとめるTxの最大件数閾値。超えたら即バッチング。
MAX_TX_PER_BATCH = 50

# 現在の動的バッチ間隔を記憶する
_current_batch_interval = 1.0

def get_dynamic_batch_interval(pending_tx_count: int) -> float:
    """
    トランザクション数や負荷状況に応じてバッチ間隔を自動決定する。
    簡易例:
      - pending_tx_count が大きいほどバッチ間隔を短くする
      - 下限は MIN_BATCH_INTERVAL
      - 何もなければゆっくり(=MAX_BATCH_INTERVAL)
    """
    global _current_batch_interval

    if pending_tx_count > MAX_TX_PER_BATCH:
        # 即バッチ化したい => 間隔を最小に
        _current_batch_interval = MIN_BATCH_INTERVAL
    elif pending_tx_count == 0:
        # 閑散 => 間隔を伸ばす
        _current_batch_interval = min(_current_batch_interval + 0.5, MAX_BATCH_INTERVAL)
    else:
        # 中間 => 緩やかに下げる
        _current_batch_interval = max(_current_batch_interval - 0.1, MIN_BATCH_INTERVAL)

    return _current_batch_interval


# -------------------------
# 6ヶ月ルール
# -------------------------
MAX_DAG_DURATION = 15552000  # 6ヶ月(秒)
ALLOW_EXTEND_DURATION = True  # Trueなら延長申請ができるとする

# -------------------------
# Erasure Coding / 冗長度
# -------------------------
# ライトノードオフライン対策として、複数コピーを格納
# ex: NUM_SHARDS=4, REDUNDANCY=4 => total 16 fragments
NUM_SHARDS = 4
REDUNDANCY = 4

# -------------------------
# ライトノードの再配布(リバランス)インターバル
# -------------------------
REBALANCE_INTERVAL = 30.0  # 30秒ごとにオフラインノードを検知し、再複製を試みる


# -------------------------
# シャーディング関数 (必要に応じて使用)
# -------------------------
def shard_and_assign_hex(hash_str: str, shard_size=16, redundancy=2, nodes=[]):
    """
    以前の実装を残しておく。shard_size=16 => 先頭1桁, 256=>先頭2桁。
    redundancy=冗長度
    """
    hex_len = 1
    if shard_size == 256:
        hex_len = 2
    shard_hex = hash_str[:hex_len]
    shard_id = int(shard_hex, 16)

    scored = []
    hash_val = int(hash_str, 16)
    for n in nodes:
        random_factor = (hash_val % 100)/100.0
        w = n.get("weight", 1.0)
        r = n.get("reliability", 0.9)
        score = w * r * (1.0 + random_factor)
        scored.append((score, n))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = scored[:redundancy]

    return {
        "shard_id": shard_id,
        "shard_hex": shard_hex,
        "assigned_nodes": [s[1] for s in selected]
    }


# -------------------------
# Rust連携 (pyo3, cffi, or grpc)
# -------------------------
def get_rust_api():
    class RustApiStub:
        def batch_verify(self, batch_data):
            # 実際はrayonなどで並列検証 => ダミー
            return batch_data
    return RustApiStub()
