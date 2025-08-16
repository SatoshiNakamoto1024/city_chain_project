# dag/dag_anchor.py
import threading

class DAGAnchor:
    def __init__(self):
        self.anchors = {}
        self.lock = threading.Lock()
    
    def set_anchor(self, checkpoint_id, anchor_value):
        with self.lock:
            self.anchors[checkpoint_id] = anchor_value
    
    def get_anchor(self, checkpoint_id):
        with self.lock:
            return self.anchors.get(checkpoint_id)
