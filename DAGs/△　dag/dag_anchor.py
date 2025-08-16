# dag/dag_anchor.py
import threading
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class DAGAnchor:
    def __init__(self):
        self.anchors = {}
        self.lock = threading.Lock()
        logger.info("DAGAnchor initialized.")

    def set_anchor(self, checkpoint_id, anchor_value):
        with self.lock:
            self.anchors[checkpoint_id] = anchor_value
            logger.info("Anchor set: %s -> %s", checkpoint_id, anchor_value)

    def get_anchor(self, checkpoint_id):
        with self.lock:
            anchor = self.anchors.get(checkpoint_id)
            logger.info("Anchor retrieved: %s -> %s", checkpoint_id, anchor)
            return anchor

if __name__ == "__main__":
    anchor = DAGAnchor()
    anchor.set_anchor("cp1", "anchor_value_1")
    print(anchor.get_anchor("cp1"))
