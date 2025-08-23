# dag/dag_handler.py
import asyncio
from uuid import uuid4
from .dag_storage import DAGStorage, DAGNode
from db_handler import save_transaction


class DAGHandler:
    def __init__(self, batch_interval=1):
        self.storage = DAGStorage()
        self.batch_interval = batch_interval

    async def add_transaction(self, sender, receiver, amount, tx_type):
        tx_id = str(uuid4())
        node = DAGNode(tx_id, sender, receiver, amount, tx_type, status="completed")
        tx_hash = node.hash
        # 同期関数を非同期で実行
        await asyncio.to_thread(self.storage.add_node, node)
        # バッチ処理を非同期タスクとしてスケジュール
        asyncio.create_task(self.delayed_batch_process(tx_id, self.batch_interval))
        return tx_id, tx_hash

    async def delayed_batch_process(self, tx_id, delay):
        await asyncio.sleep(delay)
        await self.batch_process(tx_id)

    async def batch_process(self, tx_id):
        # get_node と remove_node も同期関数なので asyncio.to_thread を利用
        node = await asyncio.to_thread(self.storage.get_node, tx_id)
        if node and node.status == "completed":
            if node.tx_type == "send":
                from consensus.distributed_storage import distribute_and_save_transaction
                await distribute_and_save_transaction(node)
            elif node.tx_type == "receive":
                tx_dict = {
                    "tx_id": node.tx_id,
                    "sender": node.sender,
                    "receiver": node.receiver,
                    "amount": node.amount,
                    "timestamp": node.timestamp,
                    "hash": node.hash,
                    "status": node.status,
                    "tx_type": node.tx_type,
                    "distribution_info": None
                }
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, save_transaction, tx_dict)
                print(f"[AsyncDAGHandler] 受信Tx {node.tx_id} をMongoDBに保存しました。")
            await asyncio.to_thread(self.storage.remove_node, tx_id)
