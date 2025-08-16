以下は、セッション管理（ログイン履歴やセッション情報の記録、参照、削除、分析など）を行うモジュール群を「session_manager」フォルダーとして分割した例です。
※ フォルダー名はハイフンが使えないため、ここでは「session_manager」としています。
本番実装用を想定し、AWS（DynamoDB）への接続、ログ記録、セッションの厳格な管理や分析機能を盛り込んだダミー実装例です。

session_manager/
├── __init__.py
├── app_session_manager.py
├── config.py
├── create_login_table.py
├── session_analysis.py
├── session_db.py
├── session_manager.py     # セッション制御（token / refresh）
├── session_service.py  

まとめ
上記7つのファイルで、実際の DynamoDB (LoginHistory テーブル) を操作しながらセッション管理を行うことができます。

起動方法
python app_session_manager.py で、main() を実行
ダミーのユーザーUUIDでログイン、セッション作成、延長、古いセッション削除、分析を行う

注意
この実装はログイン用テーブル LoginHistory を使っています。
本番運用ではGSIやセキュリティを考慮する必要があります。
各ファイルは省略せずに全文を記載しており、本番 DynamoDB および 本番 AWS 環境 で動作を確認できるはずです。
もしさらに修正点があればご連絡ください。


補足説明
session_manager/config.py
はセッション管理専用の設定項目（使用する DynamoDB テーブル名、保持期間など）を定義します。

session_manager/session_db.py
では、DynamoDB の LoginHistory テーブルを利用してセッションデータの保存、取得、古いセッションの削除を実装しています。
※ KeyConditionExpression には boto3.dynamodb.conditions.Key を使用しています。

session_manager/session_service.py
は、セッション作成（ログイン時に新規セッションの記録）、セッションの取得（重複排除など）、セッション延長や古いセッションの削除など高レベルのサービス処理を実装しています。

session_manager/session_analysis.py
は、取得したセッション履歴から平均ログイン間隔、最終ログイン時刻、セッション件数などの分析を行うサンプルです。

これらのモジュール群を組み合わせることで、ログイン時にユーザーのセッションを厳格に記録し、後でその情報を参照・分析できる仕組みが構築されます。
各機能は本番環境で必要に応じたエラーハンドリングやセキュリティ対策、効率的なクエリ処理などをさらに追加してご利用ください。


# app_session_manager.py を実行結果
PS D:\city_chain_project\login\session_manager> python app_session_manager.py
テーブル 'LoginHistory' は既に存在します。
[INFO] 2025-03-16 05:36:41,931 - == セッション管理テスト開始 ==
[INFO] 2025-03-16 05:36:41,932 - ユーザー 720b73bf-0d28-414b-9d5d-ac1fe3492a90 の新規セッションを作成します。
[INFO] 2025-03-16 05:36:43,061 - セッション記録保存成功: session_id=831d70c9-34dd-4b1e-8146-1f7ce76d40da
[INFO] 2025-03-16 05:36:43,061 - セッション記録保存成功: session_id=831d70c9-34dd-4b1e-8146-1f7ce76d40da
[INFO] 2025-03-16 05:36:43,062 - セッション作成完了: 831d70c9-34dd-4b1e-8146-1f7ce76d40da
[INFO] 2025-03-16 05:36:43,063 - 新規セッション作成完了: {'uuid': '720b73bf-0d28-414b-9d5d-ac1fe3492a90', 'session_id': '831d70c9-34dd-4b1e-8146-1f7ce76d40da', 'login_time': '2025-03-15T20:36:41.932550', 'ip_address': '127.0.0.1', 'status': 'active'}  
[INFO] 2025-03-16 05:36:43,063 - ユーザー 720b73bf-0d28-414b-9d5d-ac1fe3492a90 のログイン記録を保存します。
[INFO] 2025-03-16 05:36:44,174 - Login record saved for user: 720b73bf-0d28-414b-9d5d-ac1fe3492a90, session_id: 2ff04551-534b-4de8-80a5-dd7f49cd4b25
[INFO] 2025-03-16 05:36:44,174 - ログイン記録保存完了。
[INFO] 2025-03-16 05:36:44,175 - ユーザー 720b73bf-0d28-414b-9d5d-ac1fe3492a90 のセッション履歴を取得します。
[INFO] 2025-03-16 05:36:44,407 - セッション履歴取得成功: ユーザー 720b73bf-0d28-414b-9d5d-ac1fe3492a90 (件数=2)
[INFO] 2025-03-16 05:36:44,407 - セッション履歴取得成功: ユーザー 720b73bf-0d28-414b-9d5d-ac1fe3492a90 (件数=2)
[INFO] 2025-03-16 05:36:44,409 - 取得されたセッション一覧: [{'uuid': '720b73bf-0d28-414b-9d5d-ac1fe3492a90', 'ip_address': '127.0.0.1', 'login_time': '2025-03-15T20:36:43.064317', 'status': 'active', 'session_id': '2ff04551-534b-4de8-80a5-dd7f49cd4b25'}, {'uuid': '720b73bf-0d28-414b-9d5d-ac1fe3492a90', 'ip_address': '127.0.0.1', 'login_time': '2025-03-15T20:36:41.932550', 'status': 'active', 'session_id': '831d70c9-34dd-4b1e-8146-1f7ce76d40da'}]
[INFO] 2025-03-16 05:36:44,411 - セッション 2ff04551-534b-4de8-80a5-dd7f49cd4b25 の延長を実施します。
[INFO] 2025-03-16 05:36:44,602 - セッション更新成功: 2ff04551-534b-4de8-80a5-dd7f49cd4b25
[INFO] 2025-03-16 05:36:44,602 - セッション更新成功: 2ff04551-534b-4de8-80a5-dd7f49cd4b25
[INFO] 2025-03-16 05:36:44,605 - セッション延長結果: {'session_id': '2ff04551-534b-4de8-80a5-dd7f49cd4b25', 'new_login_time': '2025-03-15T20:36:44.412500'}
D:\city_chain_project\login\session_manager\app_session_manager.py:74: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  cutoff = datetime.utcnow() - timedelta(days=1)
[INFO] 2025-03-16 05:36:44,613 - カットオフ日時（古いセッション削除対象）: 2025-03-14T20:36:44.613246
[INFO] 2025-03-16 05:36:44,806 - 古いセッション削除完了: 0 件削除
[INFO] 2025-03-16 05:36:44,806 - 古いセッション削除完了: 0 件削除
[INFO] 2025-03-16 05:36:44,807 - 古いセッションの削除処理完了。
[INFO] 2025-03-16 05:36:45,935 - セッション分析結果: {'average_interval': 2.47995, 'last_login': '2025-03-15T20:36:44.412500', 'session_count': 2}
[INFO] 2025-03-16 05:36:45,936 - == セッション管理テスト終了 ==
 

# まとめ
DynamoDB のリージョンがコードと AWS CLI の両方で一致していることを確認してください。
コード内で環境変数 AWS_REGION を使ってリージョンを統一することで、誤ったリージョンで操作するミスを防げます。
もしコードを変更した場合は、AWS CLI で aws dynamodb scan --region us-east-1 --table-name LoginHistory など、正しいリージョンを指定してデータを確認してください。
これで、本番実装用の DynamoDB テーブルを使った状態で、データが正しく保存されているか確認できるはずです。

ありがとう！
PS C:\WINDOWS\system32> aws dynamodb scan --table-name LoginHistory --region us-east-1
>>
{
    "Items": [
        {
            "uuid": {
                "S": "5056997c-b7ad-48e9-b90c-73591c24a7ea"
            },
            "ip_address": {
                "S": "127.0.0.1"
            },
            "login_time": {
                "S": "2025-03-15T14:41:54.013470"
            },
            "status": {
                "S": "active"
            },
            "session_id": {
                "S": "6a57d50c-1f10-46c1-9c86-3fde97bebe1a"
            }
        },
        {
            "uuid": {
                "S": "5056997c-b7ad-48e9-b90c-73591c24a7ea"
            },
            "ip_address": {
                "S": "127.0.0.1"
            },
            "login_time": {
                "S": "2025-03-15T14:41:52.575583"
            },
-- More  --

それは良い結果です！
DynamoDB のテーブル「LoginHistory」に対して、us-east-1 リージョンで正常にデータが保存され、スキャン結果にセッション情報が表示されています。

この結果から、先ほどのリージョン設定の統一が正しく機能しており、コードも本番実装用の設定に沿って動作していることが確認できます。

補足
リージョンの統一:
コード内で AWS_REGION を環境変数または設定ファイルから取得しているため、AWS CLI でスキャンするときにも同じリージョン（us-east-1）を指定する必要があります。今回の結果はその点で問題なく、DynamoDB にデータが書き込まれていることが確認できました。

テーブル項目:
スキャン結果に表示される各項目（uuid, session_id, login_time, ip_address, status）は、セッション管理で意図した通りのデータが保存されていることを示しています。

今後の確認:
実際の本番環境では CloudWatch Logs などでログ出力も確認しながら、動作を監視してください。また、テスト時にデータが上書きされるなどの問題がないか、適宜チェックすることをおすすめします。


#　dilithium5 を埋め込んだので、サーバー起動は下記から
& D:\.venv\Scripts\python.exe D:\city_chain_project\login\session_manager\app_session_manager.py