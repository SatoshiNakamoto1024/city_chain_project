├── profile/
    ├── app_profile.py
    ├── profile.py    　 # プロフィール管理
    ├── profile_edit.py  # プロフィール編集
    ├── profile_data/
        ├── profile.....json    # 予備でローカル管理

ポイント:
profile_bp: /profile 下にGET/POSTを実装。
GET – ?uuid=xxx がなければ400エラー。ユーザーをDynamoDBから取得し表示。
POST – フォームから uuid と更新項目を受け取り、update_user でDynamoDB更新。結果をJSON返却。
create_app() – Flaskアプリ生成後に profile_bp を /profile prefixで登録。
単独起動 – python app_profile.py で localhost:5000/profile が有効。


# test error
このエラーは、テストでユーザー登録のために呼び出しているエンドポイント
http://192.168.3.8:5000/registration/
が存在しない（404）ために発生しています。

背景
現状のサーバー:
今回のテストは、app_profile.py（プロフィール機能を提供するサーバー）を起動している前提です。このアプリは url_prefix="/profile" のエンドポイントしか持っていません。

テストの問題点:
テストの test_post_profile_update では、まずユーザー登録API（/registration/）を呼び出そうとしていますが、プロフィールサーバーにはそのルートがないため、404が返ります。

解決方法
解決方法は２通りあります：

1. ユーザー登録APIが別のサーバー（例：app_registration.py）で提供されているなら
テスト実行時にプロフィールサーバーだけでなく、ユーザー登録用のサーバーも起動する必要があります。

その場合、テスト内で正しいURL（たとえば http://192.168.3.8:5000/registration/）に対してリクエストを送るようにします。

2. プロフィール更新のテストだけを行うため、あらかじめテスト用のユーザーをDynamoDBに直接登録して、そのユーザーのプロフィールを更新する
こちらの方法がシンプルです。

テスト側で、ユーザー登録APIを呼ばずに、直接テスト用ユーザーをDynamoDBに挿入しておき、そのユーザーの uuid を使って /profile エンドポイントに対してプロフィール更新リクエストを送るように変更します。

推奨する修正例（方法 2: プロフィール更新テスト用に直接ユーザーを登録）
以下は、test_post_profile_update の部分を修正した例です。
def test_post_profile_update():
    """
    正常系: DynamoDBに存在するユーザーのプロフィールを /profile POST でアップデートするテスト
    """
    import boto3
    from datetime import datetime
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")  # AWS_REGION も使えます
    # ユーザーテーブル名は実際の環境に合わせる（例: "UsersTable"）
    users_table = dynamodb.Table("UsersTable")
    
    # テスト用ユーザーを直接DynamoDBに登録
    test_user_uuid = str(uuid.uuid4())
    test_user_item = {
        "uuid": test_user_uuid,
        "session_id": "REGISTRATION"
        "name": "ProfileTest",
        "birth_date": "2001-01-01",
        "address": "XYZ Street",
        "mynumber": "111111111111",
        "email": f"profile_{uuid.uuid4().hex[:5]}@example.com",
        "phone": "08022223333",
        "password_hash": "dummy",  # ダミー値
        "salt": "dummy",
        "initial_harmony_token": "300",
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    users_table.put_item(Item=test_user_item)

    # /profile POST で更新
    base_url = "http://192.168.3.8:5000/profile/"
    form_data = {
        "uuid": test_user_uuid,
        "address": "Updated Street 999",
        "phone": "09077776666"
    }
    resp = requests.post(base_url, data=form_data)
    # ステータスコードは、ユーザーが更新できれば200、見つからなければ404や500になる可能性もあるので許容
    assert resp.status_code in [200, 404, 500]
    if resp.status_code == 200:
        updated_user = resp.json()
        assert updated_user["address"] == "Updated Street 999"
        assert updated_user["phone"] == "09077776666"
補足
ユーザー登録APIをテストしたい場合：
ユーザー登録APIは別のサーバー（たとえば app_registration.py で起動）で提供されるので、そのサーバーも同時に起動する必要があります。
しかし、今回の test_profile.py はプロフィール機能の統合テストなので、あらかじめテスト用のユーザーをDynamoDBに直接挿入する方法がシンプルです。

get_user() や update_user() の実装に合わせて、テストで登録するユーザー項目のキー名やテーブル名を確認してください。

結論
エラーの原因は、テストで誤ったユーザー登録エンドポイント（/registration/）にリクエストを送っていたため、404が返ってきたことです。
そのため、プロフィール更新のテストでは、ユーザー登録を直接DynamoDBに挿入して、/profile エンドポイントに対して更新リクエストを送るように変更すれば、エラーは解消されるはずです。