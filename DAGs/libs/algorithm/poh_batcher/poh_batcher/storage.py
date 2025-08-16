# D:\city_chain_project\DAGs\libs\algorithm\poh_batcher\poh_batcher\storage.py
# poh_batcher/poh_batcher/storage.py
# -----------------------------------------------------------------------------
# 汎用ストレージバックエンド
#
# * AsyncFileStorage : ローカルファイルシステム (file://)
# * S3Storage        : Amazon S3  (s3://)
#
# どちらも **非同期 API** (await save_json / await save_bytes) を統一して提供する。
#
# - save_json()  : 文字列 (JSON) を保存
# - save_bytes() : 生バイト列を保存 (gzip/zstd ペイロード用)
# - exists()     : オブジェクトの存在確認
# - get_url()    : 公開 URL (or file://…) を返す
# -----------------------------------------------------------------------------
from __future__ import annotations

import abc
import asyncio
import logging
import os
import pathlib
from typing import Optional

_LOG = logging.getLogger("poh_batcher.storage")


class StorageBackend(abc.ABC):
    @abc.abstractmethod
    async def save_json(self, key: str, text: str) -> None:
        ...

    @abc.abstractmethod
    async def save_bytes(self, key: str, data: bytes) -> None:
        ...

    @abc.abstractmethod
    async def exists(self, key: str) -> bool:
        ...

    @abc.abstractmethod
    def get_url(self, key: str) -> str:
        ...


class LocalStorage(StorageBackend):
    """
    file:/// ベースのストレージバックエンド
    """

    def __init__(self, root_dir: os.PathLike | str):
        self.root = pathlib.Path(root_dir).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        _LOG.info("LocalStorage root=%s", self.root)

    def _abs_path(self, key: str) -> pathlib.Path:
        return self.root / key.lstrip("/")

    async def save_json(self, key: str, text: str) -> None:
        path = self._abs_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, path.write_text, text, "utf-8")
        _LOG.debug("Wrote JSON %s (%d bytes)", path, len(text))

    async def save_bytes(self, key: str, data: bytes) -> None:
        path = self._abs_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, path.write_bytes, data)
        _LOG.debug("Wrote bytes %s (%d bytes)", path, len(data))

    async def exists(self, key: str) -> bool:
        path = self._abs_path(key)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, path.exists)

    def get_url(self, key: str) -> str:
        return f"file://{self._abs_path(key)}"


class S3Storage(StorageBackend):
    """
    s3://bucket[/prefix] ベースのストレージバックエンド
    * boto3 (同期) / aioboto3 (非同期) サポート
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
                _LOG.debug("aioboto3 not available, falling back to boto3")

        import boto3  # deferred
        self._boto_client = boto3.client("s3", region_name=region_name)
        _LOG.info("S3Storage bucket=%s prefix=%s", bucket, self.prefix)

    def _s3_key(self, key: str) -> str:
        return f"{self.prefix}/{key.lstrip('/')}" if self.prefix else key.lstrip("/")

    async def save_json(self, key: str, text: str) -> None:
        await self.save_bytes(key, text.encode("utf-8"))

    async def save_bytes(self, key: str, data: bytes) -> None:
        k = self._s3_key(key)
        if self._aiobot_available:
            if self._aiobot_client is None:
                self._aiobot_client = await self._aiobot_session.client("s3").__aenter__()
            await self._aiobot_client.put_object(
                Bucket=self.bucket,
                Key=k,
                Body=data,
                ContentType="application/octet-stream",
            )
        else:
            loop = asyncio.get_running_loop()
            def _put():
                self._boto_client.put_object(
                    Bucket=self.bucket,
                    Key=k,
                    Body=data,
                    ContentType="application/octet-stream",
                )
            await loop.run_in_executor(None, _put)
        _LOG.debug("Uploaded s3://%s/%s (%d bytes)", self.bucket, k, len(data))

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
        def _head() -> bool:
            from botocore.exceptions import ClientError
            try:
                self._boto_client.head_object(Bucket=self.bucket, Key=k)
                return True
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                return code in ("404", "403", "400", "NoSuchKey")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _head)

    def get_url(self, key: str) -> str:
        return f"s3://{self.bucket}/{self._s3_key(key)}"


def storage_from_url(url: str) -> StorageBackend:
    """
    "file:///path" or "/path" → LocalStorage
    "s3://bucket/prefix"    → S3Storage
    """
    if url.startswith("s3://"):
        without = url[5:]
        bucket, _, prefix = without.partition("/")
        return S3Storage(bucket=bucket, prefix=prefix)
    path = url.removeprefix("file://")
    return LocalStorage(path)


# 旧 API 名
AsyncFileStorage = LocalStorage
