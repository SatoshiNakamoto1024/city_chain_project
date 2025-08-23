# D:\city_chain_project\DAGs\libs\algorithm\poh_config\poh_config\config.py
# poh_config/config.py

import asyncio
from pathlib import Path
from typing import Optional, Callable, Any, Dict

import aiofiles

from .parsers import toml_parser, json_parser, yaml_parser

ParserFunc = Callable[[Path], asyncio.Future]

# 拡張子 → 非同期パーサ関数 のマッピング
_PARSER_MAP: Dict[str, ParserFunc] = {
    ".toml": toml_parser.parse,
    ".json": json_parser.parse,
    ".yaml": yaml_parser.parse,
    ".yml":  yaml_parser.parse,
}


class ConfigManager:
    """
    設定ファイル (TOML/JSON/YAML) の読み込み・キャッシュ・監視を提供。

    - load()       : 非同期ロード
    - load_sync()  : 同期ロード
    - get(key)     : キャッシュから値取得
    - watch(cb)    : ファイル変更の監視（非推奨、watchers.py 推奨）
    """

    def __init__(self, path: Path, fmt: Optional[str] = None):
        self._path = path
        ext = (fmt or path.suffix).lower()
        if ext not in _PARSER_MAP:
            raise ValueError(f"unsupported format/extension: {ext}")
        self._parser = _PARSER_MAP[ext]
        self._data: Optional[Dict[str, Any]] = None
        self._lock = asyncio.Lock()

    async def load(self) -> Dict[str, Any]:
        """
        非同期にファイルを読み込み、パース＆キャッシュ。常に最新の dict を返す。
        """
        async with self._lock:
            # ファイルを非同期読み込み
            async with aiofiles.open(self._path, mode="r", encoding="utf-8") as f:
                content = await f.read()
            # 非同期パーサに Path を渡す（parser が Path 受け取り型である契約）
            data = await self._parser(self._path)
            self._data = dict(data)
            return dict(self._data)

    def load_sync(self) -> Dict[str, Any]:
        """
        同期ロード。
        - 既に非同期 load() でキャッシュ済みならキャッシュを返す
        - そうでなければ、同期的にファイル読 -> テキストパース
        """
        # キャッシュ済みなら即返却
        if self._data is not None:
            return dict(self._data)

        # ファイル同期読み込み
        text = self._path.read_text(encoding="utf-8")
        ext = self._path.suffix.lower()

        # 拡張子ごとに同期パーサを import & 実行
        if ext == ".toml":
            from .parsers.toml_parser import parse_text as _parse_sync
        elif ext == ".json":
            from .parsers.json_parser import parse_text as _parse_sync
        elif ext in (".yaml", ".yml"):
            from .parsers.yaml_parser import parse_text as _parse_sync
        else:
            raise ValueError(f"unsupported format/extension: {ext}")

        data = _parse_sync(text)
        self._data = dict(data)
        return dict(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        """
        キャッシュされた設定から値を取得。
        load() または load_sync() を先に呼び出す必要あり。
        """
        if self._data is None:
            raise RuntimeError("configuration not loaded; call load() or load_sync() first")
        return self._data.get(key, default)

    async def watch(self, callback: Callable[[Dict[str, Any]], Any]) -> None:
        """
        watchfiles ベースの監視も残しつつ、テスト用互換性を担保。
        推奨は pure-polling の poh_config/watchers.py を使うこと。
        """
        # 最初に一度ロード
        await self.load()
        # watchfiles を使った簡易監視
        from watchfiles import awatch

        async for changes in awatch(str(self._path.parent)):
            for change_type, changed in changes:  # Change, str
                if Path(changed) == self._path:
                    new_cfg = await self.load()
                    await callback(new_cfg)
