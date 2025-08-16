じゃあ、DAG分析ツールもモジュール化したい。どのくらいのノードがログインし、滞在時間はどれくらい、その間に何回送信したとか、様々な分析をし、開発用に見たい。それもフォルダーにモジュール化するなら、何処に入れるの?

ログイン状況や滞在時間、送信回数などの「DAG上の動的メトリクス」を集約・可視化する分析ツールは、運用・開発向けの横断的機能なので、common/analytics パッケージとして切り出しておくのがベストです。

network/DAGs/common/
└── analytics/
    ├── __init__.py
    ├── session_metrics.py     # ノードのログイン/滞在時間集計
    ├── tx_metrics.py          # Tx送信/受信回数やレイテンシ計測
    ├── dag_topology.py        # ノード数・エッジ数・深さなどDAG構造統計
    ├── reporter.py            # 定期レポート／ダッシュボード連携（Prometheus/Grafana用）
    └── tests/
        ├── test_session_metrics.py
        ├── test_tx_metrics.py
        └── test_dag_topology.py

使いどころ
session_metrics はログイン/ログアウト時に呼び出して滞在時間を計測。

tx_metrics は dag_client.submit_transaction の前後で送信カウントと実測レイテンシを記録。

dag_topology は開発中に JSON化されたDAG構造を渡して count_nodes／depth_statistics で構造解析。

reporter はシステム起動スクリプト／Kubernetes CronJob などで 30 秒ごとに呼び出して Pushgateway へ送信し、Grafanaで可視化。

これを入れておくことで、

リアルタイムに「今何人オンラインか」「直近1分の平均レイテンシは何msか」

DAGのサイズや複雑度がどう変化しているか

を開発／運用チームが一目で把握できるようになります。これが DAG分析ツール のモジュール化です。