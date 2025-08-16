以下は “本番運用を想定した最小構成の admin モジュール” 一式です。
admin/ … 追加する新パッケージ
__init__.py … Blueprint 登録補助

routes.py … admin_bp（UI + API）

service.py … DynamoDB／CloudWatch 等の実業務ロジック

auth.py … 管理者 JWT 検証／RBAC

models.py … 共通モデル定義（必要最小限）

login_app/app_login.py に Blueprint 登録 1 行を追記

# まとめ：使い分け
状況	対応	必要権限
QRだけ紛失	既存端末で /devices/add → 新QR発行	管理者
特定端末を失効	管理画面から証明書失効 API実行	管理者／自治体
全端末をリセット	管理画面から一括失効 → ユーザーに再登録案内	管理者／自治体


# cloudwatch に出力させる
下表の 5 フォルダーは 「パッケージの init.py で共通ロギングを初期化する」 という同じパターンでそろえます。

すべて 同一内容 なのでコピペで OK／循環しても guard で 1 回しか設定されません。

フォルダー	追加／新規ファイル	置く場所	完全コード
login_app	__init__.py
(無ければ新規)	login_app/__init__.py	python\n\"\"\"login_app パッケージ初期化 & CloudWatch ロガー設定\"\"\"\nfrom infra.logging_setup import configure_logging\nconfigure_logging() # ← これだけで全モジュール共通設定\n\nimport logging\nlogger = logging.getLogger(__name__)\nlogger.debug(\"login_app package imported\")\n
registration	__init__.py	registration/__init__.py	python\n\"\"\"registration パッケージ共通設定\"\"\"\nfrom infra.logging_setup import configure_logging\nconfigure_logging()\n\nimport logging\nlogging.getLogger(__name__).debug(\"registration package imported\")\n
user_manager	__init__.py	user_manager/__init__.py	python\n\"\"\"user_manager パッケージ\"\"\"\nfrom infra.logging_setup import configure_logging\nconfigure_logging()\n
device_manager	__init__.py	device_manager/__init__.py	python\n\"\"\"device_manager パッケージ\"\"\"\nfrom infra.logging_setup import configure_logging\nconfigure_logging()\n
auth_py	__init__.py（既存なら先頭へ追記）	auth_py/__init__.py	python\nfrom infra.logging_setup import configure_logging\nconfigure_logging()\n\n# 以降は従来の公開 API re‑export など\nfrom .app_auth import *\n


補足 1 — なぜ init.py なの？
どのサブモジュールをインポートしても一番最初に package が読み込まれる →
確実に 1 度だけ configure_logging() が実行される。

補足 2 — 既存の logging.basicConfig(...) は削除
infra.logging_setup が root ハンドラを構成するので、
他の basicConfig は衝突（重複出力）を招く。
もし残っていたらコメントアウトして下さい。

補足 3 — エントリーポイント側ファイルは変更不要
たとえば login_app/app_login.py で from login_app import something と
1 行でも import すれば __init__.py が実行されるため、
個別に configure_logging() をもう呼ぶ必要はありません。

これで login_app / registration / user_manager / device_manager / auth_py
すべてが CloudWatch に一元的にログを書き出す構成になります。


# 1. Blueprint 登録：app_login.py の修正
+++ b/login_app/app_login.py
@@ -12,6 +12,8 @@ from login_app.register import register_bp
 from login_app.login_routes import login_bp
 from login_app.logout import logout_bp

+# Admin 用 Blueprint をインポート
+from login_app.admin.routes import admin_bp
 app = Flask(__name__, template_folder=template_folder)
 register_blueprint(register_bp, url_prefix="/register")
 app.register_blueprint(login_bp,    url_prefix="/login")
@@ -20,4 +22,5 @@ register_blueprint(logout_bp,   url_prefix="/logout")

 # 本番想定では JWT に admin クレームを持つユーザーだけが叩ける
 app.register_blueprint(admin_bp,     url_prefix="/admin")
+
 if __name__ == "__main__":
     app.run(host="0.0.0.0", port=6010, debug=True)


# 「Admin 系 UI／API」 と 「Municipality（自治体）用ツール」 の両方から同じ証明書失効機能を呼び出せる運用は ― 現場でもよく採られる実践パターンです。

実運用で“両方から失効”を許すときの整理ポイント
項目	具体的な考慮点	推奨アプローチ
権限制御	
• Admin は全ユーザー
• Municipality は自分の管轄ユーザーのみ （例：テナント／自治体 ID で絞り込み）	- JWT/Paseto に role と tenant_id を入れる。
- /admin/revoke_cert は role in {'admin','superadmin'}
- /municipality/revoke_cert は role == 'municipality' かつ 証明書の tenant_id が一致する場合のみ許可
コード共通化	失効処理を 2 か所に重複実装しない	- services/cert_ops.py に
python<br>def revoke_cert(uuid, who): ...<br>
- Admin も Municipality も このサービス関数を呼ぶだけ
監査ログ	どちら経由で失効したか追跡できるように	- revoke_cert() 内で CloudWatch/DynamoDB へ
  {"action":"revoke","by":who,"from":"admin_ui"} など書く
API パス	意図と責任範囲が分かるよう分離	- /admin/revoke_cert
- /municipality/revoke_cert
UI	権限に合わせて表示を変える	- 管理画面サイドバーで “Admin Tools” と “Municipality Tools” をタブ分け

参考：共通サービス関数（例）
python
Copy
Edit
# services/cert_ops.py
import datetime, logging, boto3
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
users_table = dynamodb.Table("UsersTable")
logger = logging.getLogger(__name__)

def revoke_cert(user_uuid: str, by: str, source: str):
    """共通：証明書失効ロジック
       by     : 実行した人の username / system ID
       source : 'admin_ui' | 'municipality_api' など
    """
    ts = datetime.datetime.utcnow().isoformat()
    users_table.update_item(
        Key={"uuid": user_uuid, "session_id": "REGISTRATION"},
        UpdateExpression="SET certificate.revoked = :r, "
                         "certificate.revoked_at = :t",
        ExpressionAttributeValues={":r": True, ":t": ts},
    )
    logger.info("CERT_REVOKED uuid=%s by=%s src=%s", user_uuid, by, source)
    # 監査ログ用に PutItem しても OK
    return {"success": True, "revoked_at": ts}

Admin Blueprint 側：
from services.cert_ops import revoke_cert
...
@admin_bp.post("/revoke_cert")
@require_admin  # ← デコレータで role を確認
def admin_revoke():
    data = request.get_json()
    return jsonify(revoke_cert(data["uuid"],
                               g.current_user,   # デコでセット
                               "admin_ui"))
Municipality ツール側 も同様に revoke_cert(..., source="municipality_api") を呼ぶだけ。
これで 実装は一か所・権限制御は呼び出し側で 分担できます。

