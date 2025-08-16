# D:\city_chain_project\DAGs\libs\algorithm\poh_batcher\poh_batcher\storage.py
# storage.py
# -----------------------------------------------------------------------------
# 汎用ストレージバックエンド
#
# * LocalStorage : ローカルファイルシステム
# * S3Storage    : Amazon S3  (依存: boto3 / 任意で aioboto3)
#
# どちらも **非同期 API** (await save_json(key, text)) を統一して提供する。
#
# - save_json()  : JSON 文字列を渡すと key に保存する
# - exists()     : オブジェクトの存在確認
# - get_url()    : 公開 URL (or file://…) を返す          ─ ログ／メタデータ用
# -----------------------------------------------------------------------------
from __future__ import annotations

import abc
import asyncio
import json
import logging
import os
import pathlib
import time
from typing import Optional

_LOG = logging.getLogger("poh_batcher.storage")


# =============================================================================
# 抽象ストレージインターフェイス
# =============================================================================
class StorageBackend(abc.ABC):
    @abc.abstractmethod
    async def save_json(self, key: str, text: str) -> None: ...
    @abc.abstractmethod
    async def exists(self, key: str) -> bool: ...
    @abc.abstractmethod
    def get_url(self, key: str) -> str: ...


# =============================================================================
# ローカルファイルシステム実装
# =============================================================================
class LocalStorage(StorageBackend):
    """
    file:/// ベースのストレージバックエンド
    """

    def __init__(self, root_dir: os.PathLike | str):
        self.root = pathlib.Path(root_dir).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        _LOG.info("LocalStorage root=%s", self.root)

    # ---------- util ---------------------------------------------------------
    def _abs_path(self, key: str) -> pathlib.Path:
        return self.root / key.lstrip("/")

    # ---------- impl ---------------------------------------------------------
    async def save_json(self, key: str, text: str) -> None:
        path = self._abs_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, path.write_text, text, "utf-8")
        _LOG.debug("Wrote %s (%d bytes)", path, len(text))

    async def exists(self, key: str) -> bool:
        path = self._abs_path(key)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, path.exists)

    def get_url(self, key: str) -> str:
        return f"file://{self._abs_path(key)}"


# =============================================================================
# Amazon S3 実装
# =============================================================================
class S3Storage(StorageBackend):
    """
    prefix/key.json → s3://{bucket}/{prefix}/key.json

    * boto3 / botocore に同期依存
    * ランブロッキング I/O を run_in_executor() 経由で実行
    * (Optional) aioboto3 が import 可能なら自動切換え
    """

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        region_name: Optional[str] = None,
        use_aiobot: bool = True,
    ):
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.region_name = region_name
        self._aiobot_available = False
        self._aiobot_client = None

        if use_aiobot:
            try:
                import aioboto3  # type: ignore

                self._aiobot_available = True
                self._aiobot_session = aioboto3.Session()
            except ImportError:
                _LOG.debug("aioboto3 not available – falling back to boto3")

        import boto3  # deferred import

        self._boto_client = boto3.client("s3", region_name=region_name)
        _LOG.info("S3Storage bucket=%s prefix=%s", bucket, self.prefix)

    # ---------- util ---------------------------------------------------------
    def _s3_key(self, key: str) -> str:
        return f"{self.prefix}/{key.lstrip('/')}" if self.prefix else key.lstrip("/")

    # ---------- impl ---------------------------------------------------------
    async def save_json(self, key: str, text: str) -> None:
        k = self._s3_key(key)
        if self._aiobot_available:
            if self._aiobot_client is None:
                self._aiobot_client = await self._aiobot_session.client("s3").__aenter__()
            await self._aiobot_client.put_object(
                Bucket=self.bucket,
                Key=k,
                Body=text.encode("utf-8"),
                ContentType="application/json; charset=utf-8",
            )
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                self._boto_client.put_object,
                {"Bucket": self.bucket, "Key": k, "Body": text.encode("utf-8"),
                 "ContentType": "application/json; charset=utf-8"},
            )
        _LOG.debug("Uploaded s3://%s/%s (%d bytes)", self.bucket, k, len(text))

    async def exists(self, key: str) -> bool:
        k = self._s3_key(key)
        if self._aiobot_available:
            if self._aiobot_client is None:
                self._aiobot_client = await self._aiobot_session.client("s3").__aenter__()
            try:
                await self._aiobot_client.head_object(Bucket=self.bucket, Key=k)
                return True
            except self._aiobot_client.exceptions.NoSuchKey:  # type: ignore
                return False
        loop = asyncio.get_running_loop()

        def _head():
            from botocore.exceptions import ClientError

            try:
                self._boto_client.head_object(Bucket=self.bucket, Key=k)
                return True
            except ClientError as e:
                if e.response["Error"]["Code"] in ("404", "403", "400", "NoSuchKey"):
                    return False
                raise

        return await loop.run_in_executor(None, _head)

    def get_url(self, key: str) -> str:
        return f"s3://{self.bucket}/{self._s3_key(key)}"


# =============================================================================
# ストレージファクトリー
# =============================================================================
def storage_from_url(url: str) -> StorageBackend:
    """
    "file:///path/to/dir" or "/path/to/dir" → LocalStorage
    "s3://bucket/prefix"                    → S3Storage
    """
    if url.startswith("s3://"):
        # s3://bucket[/prefix]
        without = url[5:]
        bucket, _, prefix = without.partition("/")
        return S3Storage(bucket=bucket, prefix=prefix)
    # デフォルトはローカル
    path = url.removeprefix("file://")
    return LocalStorage(path)


# =============================================================================
# スタンドアロン動作テスト
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import random
    import string
    from datetime import datetime, timezone

    parser = argparse.ArgumentParser(description="quick storage smoke‑test")
    parser.add_argument("target", help="file:///tmp or s3://bucket/prefix")
    args = parser.parse_args()

    async def _demo() -> None:
        st = storage_from_url(args.target)
        key = f"demo_{int(time.time())}.json"
        payload = {
            "msg": "hello!",
            "ts": datetime.now(timezone.utc).isoformat(),
            "rand": "".join(random.choices(string.ascii_lowercase, k=8)),
        }
        text = json.dumps(payload, ensure_ascii=False)
        await st.save_json(key, text)
        print("saved to", st.get_url(key))
        print("exists? ->", await st.exists(key))

    asyncio.run(_demo())
