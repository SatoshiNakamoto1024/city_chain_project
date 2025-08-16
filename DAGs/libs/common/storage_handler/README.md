端末ごとの「100 MB 空き保証ストレージ保存ロジック」は、先ほどの network/python/ 以下に新しく storage_handler/ モジュールとして切り出すのが自然です。全体構成の一部を抜粋するとこんなイメージになります：

    └── common/
        ├── presence/
        ├── object_processing/
        ├── storage_handler/        ← 追加！
        │   ├── __init__.py
        │   ├── base.py             # 共通インターフェース定義
        │   ├── android.py          # Android 向け保存ロジック
        │   ├── ios.py              # iPad/iOS 向け保存ロジック
        │   ├── iot.py              # IoT 向け保存ロジック
        │   ├── game_console.py     # ゲーム機向け保存ロジック
        │   └── manager.py          # デバイスタイプ判定・ハンドラ呼び出し
        └── orchestrator/

利用例
from network.python.storage_handler.manager import StorageManager

# デバイスタイプは認証情報やリクエストヘッダから取得
device_type = "android"
handler = StorageManager.get_handler(device_type)

fragment_data = b"...(2000 バイト)..."
if handler and handler.has_space(len(fragment_data)):
    ok = handler.save_fragment("tx123_frag0", fragment_data)
    if not ok:
        raise RuntimeError("保存失敗")
else:
    raise RuntimeError("空き容量不足 or 未対応デバイス")
こうしておくと──

端末種類別ロジック は storage_handler/ に集中

共通インターフェース (base.py) で後から新デバイスも追加しやすい

Orchestrator（または PoH ワーカーなど）は、環境変数や JWT 情報から device_type を受け取って
StorageManager.get_handler() で呼び出すだけ

という形で、アンドロイドでも iPad でも IoT でもゲーム機でも、すべて同じコードパスで扱えます。


📦 storage_handler モジュール ― 全体像
層、	ファイル、	役割
共通基底、	base.py、	100 MB 空き保証＋保存ロジックを実装。コンストラクタに root_dir を渡す設計で、環境変数やテスト用ディレクトリを後から柔軟に差し替え可能。
端末別ハンドラ、	android.py ios.py iot.py game_console.py、	端末種別ごとに ENV_VAR とデフォルト保存先を定義し、create() で実際の保存ディレクトリを決定。
ハンドラ統括、	manager.py、	端末種別 (android / ios / iot / game など) を文字列で受け取り、適切なハンドラインスタンスを返す。
HTTP API、	app_storage_handler.py、	FastAPI で公開：
　‣ GET /has_space … 空き容量チェック
　‣ POST /save … base-64 データをファイル保存
テスト、	tests/test_storage_handler.py、	tmp_path にルートを向け、MIN_FREE=0 にパッチして E2E で空き確認・保存・エラーパスを検証。

1. 空き容量 100 MB 保証のしくみ
MIN_FREE = 100 * 1024 * 1024  # 100 MB

def has_space(self, size: int) -> bool:
    free = shutil.disk_usage(self.root_dir).free
    return free >= size + MIN_FREE
書き込み前に必ず free >= 要求サイズ + 100 MB を確認。

端末側ストレージが逼迫していても破損しない。

2. 依存性注入 でテスト・運用を分離
各ハンドラは create() 時に環境変数を評価。
テストでは fixture で環境変数を一時的に書き換え、tmp_path へ保存。

MIN_FREE も monkeypatch.setattr(base.MIN_FREE, 0) の一行で変更可能。
→ テスト用に空き容量制限を簡単解除。

3. HTTP API（app_storage_handler.py）
Endpoint	説明	例
GET /has_space	?device_type=android&size=2048 → 100 MB 余裕判定	{"device_type":"android","size":2048,"has_space":true}
POST /save	JSON:
{"device_type":"android","name":"frag0","data":"...base64..."}	{"saved":true}

base-64 受信 → bytes に戻して保存。

未サポート端末 / 不正 base-64 は 400 BadRequest。

4. 実運用フロー
from network.DAGs.common.storage_handler.manager import StorageManager

device_type = claims["device"]           # 例: "android"
frag_bytes  = b"..."

handler = StorageManager.get_handler(device_type)
if not handler:
    raise RuntimeError("unsupported device")

if not handler.has_space(len(frag_bytes)):
    raise RuntimeError("disk almost full")

if not handler.save_fragment("tx123_S0", frag_bytes):
    raise RuntimeError("save failed")

共通コードは一切デバイス差分なし。
新デバイスを追加する場合は、
xyz.py で class XYZHandler(StorageHandlerBase) を作成

manager._HANDLER_MAP に "xyz": XYZHandler を登録
→ 既存コード変更ゼロで拡張完了。

5. CLI／サーバー利用
# HTTP サーバー起動 (ポート 8083)
python -m network.DAGs.common.storage_handler.app_storage_handler
マシン上のローカル CLI 例:
# 10KB 書けるか?
curl "http://localhost:8083/has_space?device_type=android&size=10240"

# 実際に保存
b64=$(echo -n "HelloStorage" | base64)
curl -X POST http://localhost:8083/save \
     -H "Content-Type: application/json" \
     -d "{\"device_type\":\"android\",\"name\":\"greet.txt\",\"data\":\"$b64\"}"

✅ まとめ
空き 100 MB 保証：端末ストレージ枯渇によるクラッシュを防止
拡張容易：デバイス追加は 1 クラス + 1 行登録のみ
FastAPI ラップ：マイクロサービスとしても単体ライブラリとしても利用可
テスト容易：環境変数でルート変更 + MIN_FREE パッチで副作用ゼロ

これにより 「どのデバイスでも、同じ保存 API」 を実現しつつ、
運用／テストの両面で安全かつ拡張性の高いストレージ管理レイヤーが完成します。