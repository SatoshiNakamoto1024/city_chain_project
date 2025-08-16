# \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\storage\mongodb.py
# -*- coding: utf-8 -*-
"""
非同期 MongoDB ストレージ層（Motor ↔ mongomock フォールバック）

* motor>=3 / pymongo>=4
* 保持イベントを `hold_events` コレクションへ格納
* `$group` 集計で holder_id ごとの weighted_score を計算
*   - .env / 環境変数で MONGODB_URL / MONGODB_DB を上書き
*   - 接続に失敗したら自動で in‑memory mongomock にフォールバック
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, List

import motor.motor_asyncio
from pymongo.errors import ConfigurationError, ServerSelectionTimeoutError
from pydantic import Field
from pydantic_settings import BaseSettings

from ..data_models import HoldEvent, HoldStat

__all__ = ["MongoStorage"]

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------- #
# 設定（毎回環境変数を評価）
# ---------------------------------------------------------------------------- #
class _Settings(BaseSettings):
    mongodb_url: str = Field("mongodb://localhost:27017", alias="MONGODB_URL")
    mongodb_db: str = Field("holdmetrics", alias="MONGODB_DB")

    model_config = dict(env_prefix="", case_sensitive=False)


def _current_cfg() -> _Settings:
    """常に最新の環境変数で設定を構築"""
    return _Settings()


# ---------------------------------------------------------------------------- #
# mongomock（任意依存）
# ---------------------------------------------------------------------------- #
try:
    import mongomock  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    mongomock = None

# ---------------------------------------------------------------------------- #
# メイン実装
# ---------------------------------------------------------------------------- #
class MongoStorage:
    """
    * save_event()  …… 1件挿入
    * get_stats()   …… holder_id ごとの weighted_score 取得
    * purge()       …… テスト用の全削除
    * close()       …… 接続クローズ
    """

    # ------------------------------------------------------------------ #
    # ctor
    # ------------------------------------------------------------------ #
    def __init__(self) -> None:
        self._cfg = _current_cfg()
        self._is_mock = False
        self._client = self._create_client()
        self._db = self._client[self._cfg.mongodb_db]
        self._col = self._db.hold_events
        asyncio.create_task(self._ensure_indexes())

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    async def save_event(self, event: HoldEvent) -> None:
        """HoldEvent → BSON ドキュメントとして挿入"""
        doc = event.model_dump(by_alias=True)

        # naive datetime は UTC 扱いに補正
        for key in ("start", "end"):
            if doc[key] and doc[key].tzinfo is None:
                doc[key] = doc[key].replace(tzinfo=timezone.utc)

        await self._col.insert_one(doc)  # type: ignore[attr-defined]

    async def get_stats(self) -> List[HoldStat]:
        """`end` が埋まっているレコードだけを集計"""
        pipeline: list[dict[str, Any]] = [
            {"$match": {"end": {"$ne": None}}},
            {
                "$project": {
                    "holder_id": 1,
                    "duration_s": {
                        "$divide": [{"$subtract": ["$end", "$start"]}, 1000.0]
                    },
                    "weight": 1,
                }
            },
            {
                "$match": {"duration_s": {"$gt": 0}}
            },
            {
                "$group": {
                    "_id": "$holder_id",
                    "weighted_score": {
                        "$sum": {"$multiply": ["$duration_s", "$weight"]}
                    },
                }
            },
        ]
        cursor = self._col.aggregate(pipeline)  # type: ignore[attr-defined]
        out: list[HoldStat] = []
        async for doc in cursor:
            out.append(
                HoldStat(
                    holder_id=doc["_id"],
                    weighted_score=float(doc["weighted_score"]),
                )
            )
        return out

    # テスト／メンテ用ユーティリティ
    async def purge(self) -> None:
        await self._col.delete_many({})  # type: ignore[attr-defined]

    async def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------ #
    # internal helpers
    # ------------------------------------------------------------------ #
    def _create_client(self):
        """MongoDB へ接続 or mongomock へフォールバック"""
        url = self._cfg.mongodb_url
        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(
                url,
                tz_aware=True,
                serverSelectionTimeoutMS=2_000,
            )

            # ── 接続確認：イベントループが動いていなければ同期 ping ───────
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                loop.run_until_complete(client.admin.command("ping"))
            else:
                # テストランナー内など、既存ループがある場合は非同期に確認だけ走らせる
                async def _ping():
                    try:
                        await client.admin.command("ping")
                    except Exception as exc:  # pragma: no cover
                        _LOG.warning("ping failed (ignored in running loop): %s", exc)

                asyncio.create_task(_ping())

            _LOG.info("[MongoStorage] connected to %s", url)
            return client

        except (ConfigurationError, ServerSelectionTimeoutError) as exc:
            if mongomock is None:
                raise RuntimeError(
                    f"MongoDB unreachable ({exc}) and mongomock not installed"
                ) from exc

            _LOG.warning("[MongoStorage] Mongo unreachable → mongomock (%s)", exc)
            self._is_mock = True

            # motor 風にふるまう極簡易ラッパ
            from motor.motor_asyncio import AsyncIOMotorClient

            class _AsyncMock(AsyncIOMotorClient):  # type: ignore[misc]
                def __init__(self):
                    super().__init__("mongodb://localhost")
                    self._sync = mongomock.MongoClient()

                def __getattr__(self, item):  # noqa: D401
                    return getattr(self._sync, item)

                def __getitem__(self, name):  # noqa: Dunder
                    return self._sync[name]

            return _AsyncMock()

    async def _ensure_indexes(self) -> None:
        try:
            await self._col.create_index("holder_id")
            await self._col.create_index("start")
            await self._col.create_index("end")
        except Exception as exc:  # pragma: no cover
            _LOG.warning("[MongoStorage] index creation failed: %s", exc)


# --------------------------------------------------------------------------- #
# デバッグ実行: `python -m poh_holdmetrics.storage.mongodb`
# --------------------------------------------------------------------------- #
if __name__ == "__main__":  # pragma: no cover
    import asyncio
    from datetime import timedelta

    async def _demo() -> None:
        store = MongoStorage()
        await store.purge()

        now = datetime.now(tz=timezone.utc)
        await store.save_event(
            HoldEvent(
                token_id="demo",
                holder_id="h1",
                start=now,
                end=now + timedelta(seconds=5),
                weight=2.0,
            )
        )
        stats = await store.get_stats()
        print("stats =", stats)
        await store.close()

    asyncio.run(_demo())
