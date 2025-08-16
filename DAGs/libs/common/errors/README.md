じゃあ、エラー管理をもモジュール化したい。一つずつの工程にモジュールからの呼び出しコードを配置させておき、いろんなパターンのエラーに、この場合はこう、あの場合はこう、という処理を実現するフォルダーを配置させるには何処がいい？

エラー処理はどのレイヤーにも必ず絡んできますし、後からポリシーを変えたり追加する可能性も高いので、共通モジュールとして切り出しておくのがベストです。
以下のように common/errors パッケージを作り、全体の各所から import して使う形をおすすめします。

network/DAGs/common/
└── errors/
    ├── __init__.py
    ├── exceptions.py         # 独自例外クラス定義
    ├── handlers.py           # 例外タイプ→リカバリ/通知/フォールバック処理マッピング
    ├── policies.py           # エラーポリシー（リトライ回数・タイムアウト・アラートレベル等）
    └── logger.py             # エラー専用ロガー設定


使い方例
各モジュール（transport, dag/handler, distribute_worker など）の中で…
from common.errors.exceptions import NetworkError
from common.errors.handlers import handle_error

async def submit_to_node(node, payload):
    try:
        resp = await transport.send(node, payload)
        return resp
    except grpc.RpcError as e:
        await handle_error(NetworkError(str(e)), context="submit_to_node")
        
あるいは
from common.errors.exceptions import StorageError
from common.errors.policies import STORAGE_RETRY

@retry(policy=STORAGE_RETRY)
async def store_fragment(fragment):
    try:
        result = await storage.insert(fragment)
    except Exception as e:
        raise StorageError(e)
    return result

なぜここに置くのか？
共通性: どのレイヤーでも同じ API で例外を投げ・拾える
可視性: エラー周りのロジックが散らからず一箇所で管理
柔軟性: ポリシーやハンドラを差し替えたり追加しやすい
テストしやすさ: 独立したユニットテストを用意しやすい
この構成でエラー処理を完全にモジュール化すれば、後から「このエラーはこう」「あのケースではこう」というルール変更にも即対応可能になります。


# 共通エラー基盤 common.errors の全体像
ファイル	主な役割
exceptions.py	ドメイン別の独自例外（StorageError など）と、それらの“基底”になる BaseError を定義
policies.py	例外ごとに「何秒待って何回リトライするか」「警告レベルを何にするか」などのメタ情報を持つ
handlers.py	@handle デコレーターで
① ポリシー読込み → ② ロギング → ③ 失敗時リトライ／フォールバックを実行
logger.py	例外だけを色分けフォーマットで出力する専用ロガーを生成
app_errors.py	デモ用 FastAPI。
あえて失敗する関数を用意し、共通ハンドラでレスポンスを統一
tests/	pytest -q tests/ で 3 ケース（成功・リトライ上限・バリデーション）を自動確認

1. 独自例外
class StorageError(BaseError): pass
class NetworkError(BaseError): pass
class ValidationError(BaseError): pass
BaseError を継ぐだけで 例外ファミリ に自動登録される。

追加したいときは -> 1 行で新クラスを書く → policies に追記。

2. ポリシー (policies.py)
DEFAULT_POLICY = Policy(max_attempts=5, backoff=0.2)

POLICIES = {
    StorageError: Policy(max_attempts=5, backoff=0.1),
    NetworkError: Policy(max_attempts=3, backoff=0.5),
    ValidationError: Policy(max_attempts=0)  # リトライしない
}
待ち時間(backoff) と最大リトライ回数 を一元管理。
→ インフラ変更／運用方針変更時にここだけ直せば OK。

未登録の例外は DEFAULT_POLICY が自動適用。

3. @handle デコレーター
@handle           # ←付けるだけでOK
def flaky_storage(...):
    ...
機能フロー
呼び出し関数が例外を投げる
@handle が例外型からポリシー取得
リトライ／バックオフ
ログへワーニング（レベルはポリシーに従う）

それでも失敗すれば例外をそのまま上位に再送出

4. FastAPI 連携 (app_errors.py)
例外ハンドラ (@app.exception_handler(BaseError)) を 1 つ置くだけで
ValidationError → 400
その他 → 500
ボディは {"error": "<ClassName>", "message": "..."} に統一。
失敗を検知しやすい JSON 形式なのでフロントや他サービスから扱い易い。

5. テスト (tests/test_errors.py)
テスト	何を検証しているか
test_retry_success	失敗回数 < ポリシー上限 → 最終的に 200 OK + {"result":"ok"}
test_retry_exceeded	失敗回数 > 上限 → 500 と {"error":"StorageError"}
test_validation_error	入力不足で ValidationError → 400 と {"error":"ValidationError"}

LifespanManager を使い Startup / Shutdown を確実に通すため、
テスト環境でもミドルウェアや DB クライアント初期化が走る構成にしています。

使い方 ― 自分のコードに組み込む
例外を投げる側
from errors import StorageError, handle

@handle
def save_to_db(data):
    if not db_write(data):
        raise StorageError("DB unreachable")

FastAPI ハンドラ
from fastapi import APIRouter
router = APIRouter()

@router.post("/save")
def save(data: DataModel):
    save_to_db(data)           # 失敗すると自動リトライ
    return {"status": "saved"} # 5 回失敗すると 500 JSON レスポンスが返る

別スクリプトからも再利用
try:
    save_to_db(obj)
except StorageError:
    alert_slack("DB が落ちている！")

# メリットまとめ
集中定義：再設定は policies.py と handlers.py だけ
横串ロギング：errors.logger.get_error_logger(__name__) でモジュールごとの
色付きログが生成
テストで自動保証：リグレッション時に pytest 一発で検知
アプリ層は try/except を書かずに済む：
データベース／ネットワーク／検証失敗など ドメイン例外を投げるだけ

この構成により 「どこで失敗し、何回リトライしたか」 を
統一フォーマットで把握でき、運用・監視が格段に楽になります。


