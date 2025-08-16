# D:\city_chain_project\network\sending_DAGs\python_sending\common\proto\__init__.py
"""
common.proto  パッケージ初期化

- `storage_pb2` / `storage_pb2_grpc` を import して再エクスポート
- gRPC 生成コードが行う `import common.storage_pb2` を
  sys.modules のエイリアスで解決する
"""
from importlib import import_module
import sys

# ① 生成された core message モジュールを先に import
storage_pb2 = import_module(__name__ + ".storage_pb2")

# ② エイリアスを **ここで** 登録
sys.modules.setdefault("common.storage_pb2", storage_pb2)

# ③ その後に gRPC Stub モジュールを import
storage_pb2_grpc = import_module(__name__ + ".storage_pb2_grpc")
sys.modules.setdefault("common.storage_pb2_grpc", storage_pb2_grpc)

__all__ = ["storage_pb2", "storage_pb2_grpc"]
