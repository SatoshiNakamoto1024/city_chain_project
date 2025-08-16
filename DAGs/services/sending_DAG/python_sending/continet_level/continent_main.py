# D:\city_chain_project\network\sending_DAGs\python_sending\continent_level\continent_main.py

"""
continent_main.py

大陸レベルDAGのメインエントリ。
市町村DAGからのバッチを受け取って大陸DAGに登録し、さらに分散保持などを行う。
"""

from flask import Flask, request, jsonify
from continent_dag_handler import ContinentDAGHandler

app = Flask(__name__)

# 例として "Asia" という大陸DAGとして動かす
dag_handler = ContinentDAGHandler(continent_name="Asia")

@app.route("/push_city_batch", methods=["POST"])
def push_city_batch():
    """
    市町村DAGから送られてきた未完トランザクションのバッチを受け取るAPI。
    例: {
       "batch_id": "xxx",
       "batch_hash": "abc123...",
       "tx_list": [ {...}, {...} ]
    }
    """
    data = request.get_json()
    batch_id = data.get("batch_id")
    batch_hash = data.get("batch_hash")
    tx_list = data.get("tx_list", [])

    if not batch_id or not batch_hash:
        return jsonify({"error": "Missing batch_id or batch_hash"}), 400

    dag_handler.add_city_batch(batch_id, batch_hash, tx_list)
    return jsonify({"status": "received", "batch_id": batch_id}), 200

@app.route("/complete_continent_tx/<batch_id>", methods=["POST"])
def complete_continent_tx(batch_id):
    """
    大陸DAGでバッチを完了させる場合のAPI（例）
    """
    dag_handler.mark_batch_completed(batch_id)
    return jsonify({"status": "completed", "batch_id": batch_id}), 200

if __name__ == "__main__":
    # 大陸ごとにポートを変える想定
    app.run(port=6001, debug=False)
