以下を network/DAGs/common/storage_service/ に配置してください。
service.py はご提示のまま（内部でフォールバック処理を入れてある想定）なので、
ここでは 不足分の 4 ファイル をすべてフルテキストで示します。

storage_service/
├── __init__.py
├── config.py
├── service.py
├── storage_service_impl.py
├── app_storage_service.py
└── test_storage_service.py

📦 Storage Service サブシステム – 概要
レイヤー	ファイル	役割
gRPC API 定義、	proto/storage.proto、	StoreFragment(ShardRequest) -> StoreResponse
gRPC Servicer 実装、	storage_service_impl.py、	受信したフラグメントを保存関数 _store() に委譲
サーバ起動ヘルパ、	service.py•start_storage_server()、	Servicer を登録し、任意ポートで待受
高レベルクライアント、	service.py•StorageClient、	store_fragment(tx_id, shard_id, bytes) をワンライナーで呼ぶ
実ストレージ、	distributed_storage_system.store_transaction_frag、	ノードごとに ./dist_storage/<node>/ へ JSON 保存（簡易 PoC）
常駐スクリプト、	app_storage_service.py、	python -m …app_storage_service で常駐
ユニットテスト、	tests/test_storage_service.py、	DI でフェイク保存関数を注入し E2E 検証

🔑 重要な設計ポイント ― 依存性注入（DI）
server, port = start_storage_server(
    port=0,
    node_id="my-node",
    store_func=_my_store_func,   # ← ここに好きな実装を渡せる
)

本番 … store_func を省略 ⇒ デフォルトのディスク保存実装が呼ばれる

テスト … フェイク関数を渡す ⇒ 副作用なし・呼び出し確認が容易
→ monkeypatch 依存の fragile なテストから脱却

🛠️ 使い方
1. サーバをローカル起動
python -m network.DAGs.common.storage_service.app_storage_service
# → [StorageService] listening on 50061
ポートは環境変数 STORAGE_PORT、ノード ID は node_id 引数で変更可能。

2. クライアントから保存
from network.DAGs.common.storage_service.service import StorageClient

cli = StorageClient("localhost:50061")
resp = cli.store_fragment("tx-42", "S3", b'{"foo":"bar"}')
assert resp.success

3. 別実装に差し替える
def save_to_minio(node_id, tx_id, shard_id, data):
    # MinIO / S3 の put_object() など
    ...
    return True

server, port = start_storage_server(store_func=save_to_minio)

4. プロトコル定義を変更したら再生成
# ルートで実行
python -m grpc_tools.protoc \
  -I network/DAGs/common/proto \
  --python_out=. \
  --grpc_python_out=. \
  network/DAGs/common/proto/storage.proto
option python_package = "network.DAGs.common.proto"; を
storage.proto に入れておくと生成コードは常に相対 import になります。

⚙️ 実行フロー
sequenceDiagram
    participant Client
    participant gRPC as StorageServiceImpl
    participant Store as store_transaction_frag

    Client->>gRPC: StoreFragment(tx_id,S#,…)
    gRPC->>Store: _store(node_id, tx_id, shard_id, {"raw":json})
    Note right of Store: 本番=ディスク書込\nテスト=フェイク
    Store-->>gRPC: bool
    gRPC-->>Client: StoreResponse{success, message}

✅ テスト戦略
tests/test_storage_service.py では
start_storage_server(store_func=_fake_store)
としてサーバを立て、本物の gRPC 経路を通したうえで
フェイク関数が呼び出されたかを _calls に記録して検証。
gRPC・proto・DI の 3 点を 一本のテストで E2E で担保できます。

これで トランザクションのフラグメントを任意ストレージに保存するマイクロサービスが完成し、
▸ 本番: デフォルト実装 / S3 等に差替え
▸ テスト: 副作用ゼロ
▸ クライアント: ワンライナー呼び出し
という 疎結合で保守しやすい構成になりました。
