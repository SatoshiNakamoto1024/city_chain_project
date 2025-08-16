
import time
import threading
import hashlib
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class DAGNode:
    def __init__(self, tx_id, sender, receiver, amount, tx_type, status="pending"):
        self.tx_id = tx_id
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.tx_type = tx_type  # "send" または "receive"
        self.status = status    # "pending" または "completed"
        self.timestamp = time.time()
        self.hash = self.compute_hash()
        logger.info("DAGNode created: %s", self.tx_id)
    
    def compute_hash(self):
        data = f"{self.tx_id}{self.sender}{self.receiver}{self.amount}{self.tx_type}{self.timestamp}"
        computed = hashlib.sha256(data.encode()).hexdigest()
        logger.debug("Computed hash for node %s: %s", self.tx_id, computed)
        return computed

class DAGStorage:
    def __init__(self):
        self.nodes = {}  # tx_id -> DAGNode
        self.lock = threading.Lock()
        logger.info("DAGStorage initialized.")

    def add_node(self, node):
        with self.lock:
            self.nodes[node.tx_id] = node
            logger.info("Node %s added to storage.", node.tx_id)

    def get_node(self, tx_id):
        with self.lock:
            node = self.nodes.get(tx_id)
            logger.info("Node %s retrieved from storage.", tx_id)
            return node

    def remove_node(self, tx_id):
        with self.lock:
            if tx_id in self.nodes:
                del self.nodes[tx_id]
                logger.info("Node %s removed from storage.", tx_id)

    def get_all_nodes_by_type(self, tx_type):
        with self.lock:
            result = [node for node in self.nodes.values() if node.tx_type == tx_type]
            logger.info("Retrieved %d nodes of type %s.", len(result), tx_type)
            return result

if __name__ == "__main__":
    node = DAGNode("tx_test", "Alice", "Bob", 100, "send")
    storage = DAGStorage()
    storage.add_node(node)
    retrieved = storage.get_node("tx_test")
    print(retrieved.tx_id if retrieved else "None")
