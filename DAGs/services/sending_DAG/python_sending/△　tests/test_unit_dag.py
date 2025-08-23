# D:\city_chain_project\network\DAGs\python\tests\test_unit_dag.py

"""
test_unit_dag.py

DAGハンドラ(CityDAGHandlerなど)のユニットテスト例。
Flaskサーバ起動せずに、直接クラスをインスタンス化してメソッドを呼ぶ。
"""

from city_level.city_dag_handler import CityDAGHandler


def test_add_transaction():
    dag = CityDAGHandler(city_name="TestCity")
    tx_id, tx_hash = dag.add_transaction("Alice", "Bob", 50, "send")
    assert tx_id is not None
    assert tx_hash is not None
    assert len(dag.pending_txs) == 1


def test_process_batch_empty():
    dag = CityDAGHandler(city_name="TestCity")
    # pending_txs 空の場合は何もしない
    dag._process_batch()
    assert len(dag.storage.nodes) == 0
