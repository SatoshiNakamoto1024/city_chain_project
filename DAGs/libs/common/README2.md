#　dilithium5 を埋め込んだので、python312でのサーバー起動は下記から
# まずはpython312に各種インストール
作業	具体例
3.12のPython.exeを確認	（なければインストール）
D:\Python\Python312\python.exe -m venv D:\city_chain_project\.venv312
作ったあと、
D:\city_chain_project\.venv312\Scripts\activate.bat
という具合に、仮想にはいること。


# 上記 storage.proto はコンパイル済みのものが storage_pb2.py / storage_pb2_grpc.py を生成している想定です。

python -m grpc_tools.protoc \
	  -I network/sending_DAG/python_sending/common/proto \
	  --python_out=network/sending_DAG/python_sending/common/proto \
	  --grpc_python_out=network/sending_DAG/python_sending/common/proto \
	  network/sending_DAG/python_sending/common/proto/storage.proto

# テスト結果の読み ⻑し（要点）
項目	結果	内容	補足
test_dynamic_batch_interval	PASSED	config.get_dynamic_batch_interval() の可変ロジックが期待どおり機能	common/config.py の計算が壊れていないことを確認
test_save_tx	SKIPPED	MongoDB 接続情報（MONGODB_URI 環境変数など）が設定されていないためスキップ	CI で外部 DB を要求しないよう意図的に skip する仕組み
test_distributed_storage	PASSED	断片ファイルの保存／復元 (distributed_storage_system) が正常	ローカル FS 上での簡易冗長ストレージが動く

合計 2 pass / 1 skip / 0 fail なのでユニットテストとしては成功です。

それでも最後に出た ResourceWarning
ResourceWarning: Unclosed MongoClient ...
common/db_handler.py が import された時点で グローバルに
client = MongoClient(MONGODB_URI)
を実行しているため、テスト終了後に close されず 警告が出ています
（pytest はファイルを import→テスト→プロセス終了、の順に走るだけなので）。

対処パターン
方法	具体策
1. Lazy 接続	client = None にしておき、関数内で MongoClient() を生成し with または finally: client.close() で閉じる
2. atexit で自動 close	import atexit; atexit.register(client.close) を db_handler に追記
3. テスト側で close	request.addfinalizer(common.db_handler.client.close) を fixture に書く
4. 警告を無視	pytest.ini に filterwarnings = ignore::ResourceWarning:.*MongoClient

本番コードでは 1 か 2 が推奨です。

いま出来ていること
common パッケージ が import 経由で再エクスポートされるよう構成済み
import common as C
C.config.MIN_BATCH_INTERVAL
モジュール単体テストはすべて通過（MongoDB が無い環境でも崩れない）

# セキュリティ対応の観点
この common パッケージ自体には暗号・認証コードは含まれません
（gRPC 側で mTLS／トークン認証を担保済み）
DB 接続文字列は 環境変数 読み込みでハードコードを避ける
分散ストレージはローカル FS デモ — 本番では IPFS/S3 などに差し替え前提

# これからやること（例）
1.db_handler の接続管理を改善
lazy / context-manager で ResourceWarning 解消
非同期パス（Motor）もここに統合するとテストが楽

2.storage.proto の実装
storage_pb2.py / _grpc.py を自動生成 → storage_service.py を実装

3.common.app_common CLI 拡充
batch, save, store 以外に rebalance, reward-distribute など追加

4.CI ワークフロー
MongoDB を docker-compose で立てる or test_save_tx をモックに置換

5.パッケージ化
pyproject.toml を置いて pip install -e . で import パス問題を根治

これで “common モジュールが外部から呼び出せる & テストで壊れていない” という
段階まではクリアできています。


# 設計上のワンポイント
MongoDB コレクション設計
transactions_raw で未整形 JSON を一旦保存 → 非同期ワーカーが dag_nodes に正規化して DAG にリンク
DAG ノードは { _id, tx_id, parent_ids: [], payload, ts }、インデックスは tx_id と parent_ids 配列要素

Idempotency
gRPC 受信側で tx_id が既存かを upsert 判定して二重投入を防止。
PoH・PoP など重い計算
Rust 実装を pyo3 でラップし、Python 側ワーカーから asyncio.to_thread() で呼ぶ
計算結果は DAG ノードにハッシュとして埋め込むと後段バリデータで再検証しやすい。

ロードバランス／水平分割
ChannelFactory は単一 endpoint 指定だが、pick_first → round_robin に将来スイッチできるよう、エンドポイントリストを維持。

Observability
Prometheus Interceptor + MongoDB メトリクスコレクタで「Tx/s」「承認遅延」グラフを可視化。Grafana ダッシュボード例を ./docs/observability/ に置いておくと運用が楽。

いま相談したほうが良さそうな点
・DAG の親子判定ロジック
何をもって parent-edge とするか？ PoH 時間順？ 依存トランザクション？
ここで設計が変わると Mongo スキーマも変わるので早めに確定をおすすめ。

・送信-受信の境界
sending_DAG と receiving_DAG でコードを複製せず、共通アルゴリズムを common/dag_core/ に切り出すか？
受信側は PoP 判定→代表者選出→承認という追加ステップがあるが、DAG 構築部分は共通化可能。

・gRPC サーバ実装の DI
現状 CityDAGHandler を直接 import していますが、Factory パターンで City 名→Handler を動的解決するとテストが楽。
