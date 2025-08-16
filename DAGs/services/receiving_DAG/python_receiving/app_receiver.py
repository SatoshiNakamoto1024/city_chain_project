"""
python receiver_app.py pem/client.pem
"""
import sys, json, base64, time, random
from pathlib import Path
from receiving_DAG.python import RecoveryManager
from poh_python import build_poh_ack

pem_path = Path(sys.argv[1])
rm = RecoveryManager(pem_path)

# 送信側Tx
fresh = {"tx_id":"tx123","sender":"Alice","receiver":"Bob","amount":1}
# 復元要求
rm.trigger_repair("tx123", "RequesterNode")

# 5 個 PoH_ACK をネットワーク越しに受信 sim
for i in range(5):
    node_id = f"Node{i}"
    poh = build_poh_ack(fresh, node_id, "dead")
    rm.push_incoming(poh)

# ダミー REPAIR_ACK
ack = {
    "tx_id": str(random.randint(1,9)*111),
    "tx_type":"repair_ack",
    "original_tx_id":"tx123",
    "responder":"Node0",
    "timestamp": time.time(),
    "recovered_tx": fresh,
    "signature": base64.b64encode(b"SIG_dummy").decode()
}
rm.push_incoming(ack)

time.sleep(1)
print("Done.")
