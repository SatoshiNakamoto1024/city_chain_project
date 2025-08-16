# main.py
from flask import Flask, request, jsonify
from dag.dag_handler import DAGHandler

app = Flask(__name__)
dag_handler = DAGHandler(batch_interval=1)

@app.route("/send_transaction", methods=["POST"])
def send_transaction():
    data = request.get_json()
    sender = data.get("sender")
    receiver = data.get("receiver")
    amount = data.get("amount")
    tx_side = data.get("tx_side", "send")  # "send" をデフォルト
    if not sender or not receiver or amount is None:
        return jsonify({"error": "Missing fields"}), 400
    tx_id, tx_hash = dag_handler.add_transaction(sender, receiver, amount, tx_side)
    return jsonify({"tx_id": tx_id, "tx_hash": tx_hash})

@app.route("/receive_transaction", methods=["POST"])
def receive_transaction():
    data = request.get_json()
    sender = data.get("sender")
    receiver = data.get("receiver")
    amount = data.get("amount")
    if not sender or not receiver or amount is None:
        return jsonify({"error": "Missing fields"}), 400
    tx_id, tx_hash = dag_handler.add_transaction(sender, receiver, amount, "receive")
    return jsonify({"tx_id": tx_id, "tx_hash": tx_hash})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
