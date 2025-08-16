TTL Management Module – receiving_DAG/python/ttl/

目的：未完了 Tx / PoH / RepairReq が長時間残りすぎないようにメモリ解放しつつ、
TTL 超過で自動 REPAIR_REQ を発行する“自律リーククリーナー”。

設計指針

TTLConfig に秒数・GC 間隔・REPAIR 閾値を集中定義

TTLWatchDog がバックグラウンド Thread で走り

dag_store.nodes を走査

tx_typeごとに TTL ルール分岐

期限切れ Tx は on_expire_callback(tx) で外部へ通知

RepairTrigger を recovery.repair_manager に組み込み、
WatchDog から渡された未保持 Tx に自動 REPAIR_REQ を発行

receiving_DAG/
  python/
    ttl/
      __init__.py
      config.py
      watchdog.py

ttl/config.py