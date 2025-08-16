from .models import BaseTx
from network.sending_DAG.python_sending.core.handler import CityDAGHandler
from network.sending_DAG.python_sending.core.tx_node import TxNode

def to_dag_node(tx: BaseTx) -> TxNode:
    """
    PydanticモデルからDAG側のノードオブジェクトへ変換
    """
    return TxNode(
        tx_id=tx.tx_id,
        tx_type=tx.type,
        payload=tx.dict(exclude={"type", "tx_id", "timestamp"}),
        timestamp=tx.timestamp.isoformat()
    )

async def ingest_and_submit(handler: CityDAGHandler, raw: dict):
    """
    1) JSONスキーマチェック
    2) Pydanticモデル化
    3) DAGノード化
    4) CityDAGHandlerへ登録
    """
    from .validator import parse_and_validate
    ptx = parse_and_validate(raw)
    node = to_dag_node(ptx)
    await handler.add_transaction(node)
