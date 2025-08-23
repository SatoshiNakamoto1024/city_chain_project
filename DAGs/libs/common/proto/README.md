

# D:\city_chain_project\  の位置で下記を実行
python -m grpc_tools.protoc -Inetwork/DAGs/common/proto --python_out=network/DAGs/common/proto --grpc_python_out=network/DAGs/common/proto network/DAGs/common/proto/storage.proto

そうすると、proto生成される。


# 何が起きているか
VersionError: gencode 6.30.0  runtime 5.29.5
**storage_pb2.py を生成した protoc/grpcio-tools は v 6.30.0 系
→ 生成コード先頭に ValidateProtobufRuntimeVersion(6,30,0…) が書かれた

**実行環境 (requirements.txt) の protobuf ランタイムは v 5.29.5

起動時チェックが「メジャーバージョン (6 vs 5) が違う」と落ちる

解決パターン
方式	生成コード側	ランタイム側	影響
A. ランタイムを 6.x へ上げる	そのまま	protobuf>=6.30	OpenTelemetry 1.34.x と衝突
B. storage_pb2 を 5.x で再生成	再生成	既存 protobuf<5	依存衝突なし ✔

すでに他のサブシステム（Observability）が protobuf<5 を前提に動いているので
B: “再生成” を推奨します。

開発 or CI venv で 旧 grpcio-tools を入れる
pip install "grpcio-tools<=1.59" "protobuf<5"

再生成
python -m grpc_tools.protoc -I network/DAGs/common/proto
--python_out=network/DAGs/common/proto
--grpc_python_out=network/DAGs/common/proto
network/DAGs/common/proto/storage.proto

生成された storage_pb2.py 先頭の
runtime_version.ValidateProtobufRuntimeVersion(6, ... が
ValidateProtobufRuntimeVersion(4, ...) など 5 未満 になっていることを確認。

commit ＆ 本番 venv（protobuf<5）のまま起動すると エラー解消。
