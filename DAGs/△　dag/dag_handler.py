# dag/dag_handler.py
import asyncio
from uuid import uuid4
from .dag_storage import DAGStorage, DAGNode
from db_handler import save_transaction
import time
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class DAGHandler:
    def __init__(self, batch_interval=1):
        self.storage = DAGStorage()
        self.batch_interval = batch_interval
        logger.info("DAGHandler initialized with batch_interval: %s", batch_interval)

    async def add_transaction(self, sender, receiver, amount, tx_type):
        tx_id = str(uuid4())
        node = DAGNode(tx_id, sender, receiver, amount, tx_type, status="completed")
        tx_hash = node.hash
        try:
            await asyncio.to_thread(self.storage.add_node, node)
        except Exception as e:
            logger.error("Error adding node: %s", e)
            raise
        asyncio.create_task(self.delayed_batch_process(tx_id, self.batch_interval))
        return tx_id, tx_hash

    async def delayed_batch_process(self, tx_id, delay):
        await asyncio.sleep(delay)
        await self.batch_process(tx_id)

    async def batch_process(self, tx_id):
        try:
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
                    logger.info("[DAGHandler] 受信Tx %s をMongoDBに保存しました。", node.tx_id)
                await asyncio.to_thread(self.storage.remove_node, tx_id)
                logger.info("Batch process completed for tx_id: %s", tx_id)
        except Exception as e:
            logger.error("Error in batch processing for tx_id %s: %s", tx_id, e)


if __name__ == "__main__":
    import asyncio
    import hashlib
    class DummyDAGNode:
        def __init__(self, tx_id, hash_val, sender, receiver, amount, tx_type):
            self.tx_id = tx_id
            self.hash = hash_val
            self.sender = sender
            self.receiver = receiver
            self.amount = amount
            self.tx_type = tx_type
            self.timestamp = time.time()
    dummy_data = "advanced dummy data for full consensus simulation with mysticeti fast path"
    dummy_hash = hashlib.sha256(dummy_data.encode()).hexdigest()
    dummy_node = DummyDAGNode("tx_dummy", dummy_hash, "Alice", "Bob", 100, "send")
    async def test_handler():
        handler = DAGHandler(batch_interval=1)
        tx_id, tx_hash = await handler.add_transaction("Alice", "Bob", 100, "send")
        print("Transaction added:", tx_id, tx_hash)
    asyncio.run(test_handler())
