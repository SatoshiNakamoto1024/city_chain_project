# D:\city_chain_project\network\sending_DAG\python_sending\city_level\city_main.py

"""
city_main.py

市町村レベルのDAGノードを起動するエントリポイント（Flaskサーバ）。
ユーザからの送信・受信トランザクションを受け取り、CityDAGHandlerへ連携。
"""

from flask import Flask, request, jsonify
from city_dag_handler import CityDAGHandler

app = Flask(__name__)

# 例として "NewYork" という市町村DAGとして動かす
dag_handler = CityDAGHandler(city_name="NewYork")

@app.route("/send_tx", methods=["POST"])
def send_tx():
    data = request.get_json()
    sender = data.get("sender")
    receiver = data.get("receiver")
    amount = data.get("amount", 0)
    if not sender or not receiver:
        return jsonify({"error": "Missing fields"}), 400

    tx_id, tx_hash = dag_handler.add_transaction(sender, receiver, amount, "send")
    return jsonify({"tx_id": tx_id, "tx_hash": tx_hash}), 200

@app.route("/receive_tx", methods=["POST"])
def receive_tx():
    data = request.get_json()
    sender = data.get("sender")
    receiver = data.get("receiver")
    amount = data.get("amount", 0)
    if not sender or not receiver:
        return jsonify({"error": "Missing fields"}), 400

    tx_id, tx_hash = dag_handler.add_transaction(sender, receiver, amount, "receive")
    return jsonify({"tx_id": tx_id, "tx_hash": tx_hash}), 200

@app.route("/complete_tx/<tx_id>", methods=["POST"])
def complete_tx(tx_id):
    dag_handler.mark_transaction_completed(tx_id)
    return jsonify({"status": "completed", "tx_id": tx_id}), 200

@app.route("/repair_request", methods=["POST"])
def repair_request():
    data = request.get_json()
    tx_id = data.get("tx_id")
    requester = data.get("requester")

    if not tx_id or not requester:
        return jsonify({"error": "Missing tx_id or requester"}), 400

    # 新しいTxとしてREPAIR_REQを生成
    timestamp = time.time()
    raw = f"{tx_id}|{requester}|{timestamp}"
    dummy_sig = f"REPAIR_SIG({raw})"  # 署名ダミー（実際はDilithiumで）
    dummy_enc = f"ENC({dummy_sig})"   # 暗号化ダミー（NTRUで）

    repair_tx = {
        "tx_id": str(uuid.uuid4()),
        "original_tx_id": tx_id,
        "requester": requester,
        "timestamp": timestamp,
        "signature": dummy_sig,
        "encrypted_sig": dummy_enc,
        "tx_type": TxType.REPAIR_REQ.value
    }

    dag_handler.add_raw_tx(repair_tx)
    return jsonify({"status": "repair_requested", "tx_id": repair_tx["tx_id"]}), 200

if __name__ == "__main__":
    # 市町村ごとにポートを変えてもよい
    app.run(port=5001, debug=False)
