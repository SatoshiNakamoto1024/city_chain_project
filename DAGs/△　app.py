# app.py
"""
この app.py は、DAG関連の処理に特化したエントリーポイントです。
送信トランザクション（tx_type="send"）は、DAGに一時保存され、1秒後にバッチ処理で
DAG分散保存アルゴリズムを呼び出して外部分散ストレージへ保存されます。
"""

from flask import Flask, request, jsonify
from dag.dag_handler import DAGHandler

app = Flask(__name__)

# DAGHandlerの初期化（バッチ保持時間は1秒）
dag_handler = DAGHandler(batch_interval=1)

@app.route("/send_transaction", methods=["POST"])
def send_transaction():
    """
    送信トランザクション（tx_type="send"）を受け付け、DAGに登録します。
    1秒後、バッチ処理で分散保存アルゴリズムが起動され、データが外部分散ストレージへ保存されます。
    """
    data = request.get_json()
    sender = data.get("sender")
    receiver = data.get("receiver")
    amount = data.get("amount")
    
    if not sender or not receiver or amount is None:
        return jsonify({"error": "Missing required fields"}), 400

    tx_id, tx_hash = dag_handler.add_transaction(sender, receiver, amount, tx_type="send")
    response = {
        "tx_id": tx_id,
        "tx_hash": tx_hash,
        "message": "Send transaction scheduled for DAG distributed storage."
    }
    return jsonify(response)

@app.route("/receive_transaction", methods=["POST"])
def receive_transaction():
    """
    受信トランザクション（tx_type="receive"）を受け付け、DAGに登録します。
    1秒後、直接MongoDBに保存され、DAGから削除されます。
    """
    data = request.get_json()
    sender = data.get("sender")
    receiver = data.get("receiver")
    amount = data.get("amount")
    
    if not sender or not receiver or amount is None:
        return jsonify({"error": "Missing required fields"}), 400

    tx_id, tx_hash = dag_handler.add_transaction(sender, receiver, amount, tx_type="receive")
    response = {
        "tx_id": tx_id,
        "tx_hash": tx_hash,
        "message": "Receive transaction scheduled for MongoDB storage."
    }
    return jsonify(response)

@app.route("/status", methods=["GET"])
def status():
    """
    シンプルなシステムステータス確認用エンドポイント。
    現在、DAGに保持中のトランザクションの件数（送信・受信）を返します。
    """
    send_count = len(dag_handler.storage.get_all_nodes_by_type("send"))
    receive_count = len(dag_handler.storage.get_all_nodes_by_type("receive"))
    total = send_count + receive_count
    response = {
        "send_count": send_count,
        "receive_count": receive_count,
        "total_dag_nodes": total
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
