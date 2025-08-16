import asyncio
import time
from typing import List
from .selector import pick_next_node
from .sender import send_poh_request, PoHResponse

class StoreCoordinator:
    """
    タイムキーパー付き 分散保存調整クラス
    - ノードリストを順番に試し、100ms以内に PoH_ACK を得られなければ fallback
    """
    def __init__(self, node_ids: List[str], timeout_ms: int = 100):
        self.node_ids = node_ids
        self.timeout = timeout_ms / 1000.0  # 秒
        self.attempted = set()

    async def store_with_timeout(self, tx_id: str, payload: str) -> PoHResponse:
        """
        tx_id, payload を使って各ノードへ PoH_REQUEST。
        最初に返ってきた PoH_ACK を返却。
        タイムアップなら ClientError を raise。
        """
        deadline = time.monotonic() + self.timeout
        # ノードは selector で順番 or 重み付け制御可能
        for node in pick_next_node(self.node_ids):
            if time.monotonic() >= deadline:
                break
            if node in self.attempted:
                continue
            self.attempted.add(node)
            try:
                resp = await send_poh_request(node, tx_id, payload, timeout=deadline - time.monotonic())
                if resp.success:
                    return resp
            except Exception:
                # 失敗したら次にフェイルオーバー
                continue

        # 100ms以内に誰からも返ってこなかった ⇒ フルノード fallback
        raise TimeoutError(f"store timeout for tx={tx_id}")
