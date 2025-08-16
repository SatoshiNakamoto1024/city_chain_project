
"""
TTLWatchDog – OutgoingDAG / DAGStore に対して TTL を監視し、
期限切れエントリを自動削除 or RepairReq 再送を呼び出す。
"""
from threading import Thread
import time
from typing import Callable, TYPE_CHECKING
from ..core.models import TxType, BaseTx
from ..ttl.config import TTLConfig

if TYPE_CHECKING:  # 遅延 import 用 (型チェック時のみ)
    from ..storage.dag_store import DAGStore

class TTLWatchDog:
    def __init__(self, dag: "DAGStore", cfg: TTLConfig,
                 on_expire: Callable[[BaseTx], None]):
        self.dag   = dag
        self.cfg   = cfg
        self.cb    = on_expire
        Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            time.sleep(self.cfg.GC_INTERVAL)
            now = time.time()
            dead = []
            for tx_id, tx in list(self.dag.nodes.items()):
                if self._is_expired(tx, now):
                    dead.append(tx)
                    if len(dead) >= self.cfg.GC_BATCH:
                        break
            for tx in dead:
                self.cb(tx)
                self.dag.nodes.pop(tx.tx_id, None)
                self.dag.edges.pop(tx.tx_id, None)

    # ---------------- internal ----------------
    def _is_expired(self, tx: BaseTx, now: float) -> bool:
        dt = now - tx.timestamp
        t  = tx.tx_type
        c  = self.cfg
        if t == TxType.FRESH_TX and dt > c.FRESH_TX_TTL:       return True
        if t == TxType.POH_REQUEST and dt > c.POH_REQ_TTL:      return True
        if t == TxType.POH_ACK     and dt > c.POH_ACK_TTL:      return True
        if t == TxType.REPAIR_REQ  and dt > c.REPAIR_REQ_TTL:   return True
        if t == TxType.REPAIR_ACK  and dt > c.REPAIR_ACK_TTL:   return True
        return False