# D:\city_chain_project\network\sending_DAGs\python_sending\global_level\global_main.py

"""
global_main.py

グローバルDAGのメインエントリ。
大陸DAGからのバッチを受け取ってグローバルDAGに登録、immuDBなどへの書き込みを行う想定。
"""

from flask import Flask, request, jsonify
from global_dag_handler import GlobalDAGHandler

app = Flask(__name__)
dag_handler = GlobalDAGHandler()

@app.route("/push_continent_batch", methods=["POST"])
def push_continent_batch():
    """
    大陸レベルDAGから送られてきたバッチを受け取るAPI。
    例: {
       "continent_batch_id": "xxx",
       "continent_hash": "...",
       "continent": "Asia",
       "batched_data": [...]
    }
    """
    data = request.get_json()
    c_batch_id = data.get("continent_batch_id")
    c_hash = data.get("continent_hash")
    c_name = data.get("continent", "Unknown")
    b_data = data.get("batched_data", [])

    if not c_batch_id or not c_hash:
        return jsonify({"error": "Missing continent batch info"}), 400

    dag_handler.add_continent_batch(c_batch_id, c_hash, c_name, b_data)
    return jsonify({"status": "global_received", "continent_batch_id": c_batch_id}), 200

@app.route("/complete_global_tx/<c_batch_id>", methods=["POST"])
def complete_global_tx(c_batch_id):
    dag_handler.mark_global_batch_completed(c_batch_id)
    return jsonify({"status": "completed", "c_batch_id": c_batch_id}), 200

if __name__ == "__main__":
    app.run(port=7001, debug=False)
