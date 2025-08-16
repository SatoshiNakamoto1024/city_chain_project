# dag/dag_storage.py
import time
import threading
import hashlib

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
    
    def compute_hash(self):
        data = f"{self.tx_id}{self.sender}{self.receiver}{self.amount}{self.tx_type}{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()

class DAGStorage:
    def __init__(self):
        self.nodes = {}  # tx_id -> DAGNode
        self.lock = threading.Lock()
    
    def add_node(self, node):
        with self.lock:
            self.nodes[node.tx_id] = node
    
    def get_node(self, tx_id):
        with self.lock:
            return self.nodes.get(tx_id)
    
    def remove_node(self, tx_id):
        with self.lock:
            if tx_id in self.nodes:
                del self.nodes[tx_id]
    
    def get_all_nodes_by_type(self, tx_type):
        with self.lock:
            return [node for node in self.nodes.values() if node.tx_type == tx_type]
