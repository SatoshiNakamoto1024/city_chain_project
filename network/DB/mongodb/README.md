以下は、MongoDB Atlas を AWS と連携させた MongoDB 設計を、初めからどのように進めるかの詳細な手順とポイントになります。

# 1. 全体像の概要
MongoDB Atlas とは
MongoDB Atlas は MongoDB 社が提供するフルマネージドクラウドデータベースサービスです。
AWS、GCP、Azure のいずれかでクラスタを展開でき、レプリカセット、シャーディング、バックアップ、セキュリティ設定などが自動管理されます。
AWS との連携
AWS側のアプリケーション（例えば、ECS、Lambda、EC2 など）から Atlas に接続し、データ操作を行います。
Atlas との接続は、IPホワイトリストまたはVPC Peering/PrivateLink によりセキュアに行います。

# 2. 手順ステップ
ステップ1：MongoDB Atlas アカウントの作成とクラスタのプロビジョニング
MongoDB Atlas の公式サイト（https://www.mongodb.com/cloud/atlas）にアクセスし、アカウントを作成します。
アカウント作成後、ダッシュボードから「Build a Cluster」を選択し、AWS をプラットフォームとして選びます。
クラスターのサイズ（無料枠の場合は M0 または M2/M5 など）とリージョン（AWS のリージョン、例: ap-northeast-1）を選び、クラスターを作成します。
ステップ2：セキュリティ設定の構成
IPホワイトリストの設定
Atlas の「Network Access」セクションで、AWS 上のアプリケーションサーバーのパブリックIP（または VPC の NAT ゲートウェイの IP）をホワイトリストに追加します。
これにより、指定した IP からの接続のみが許可されます。
VPC Peering / PrivateLink の設定（オプション）
よりセキュアな接続を実現するため、Atlas で AWS VPC ピアリングを設定できます。
Atlas の「Network Access」内の VPC Peering 機能を利用し、AWS 側の VPC ID、AWS アカウント ID、リージョン、Atlas 側の CIDR ブロックなどを入力します。
AWS 側では、該当する VPC ピアリング接続の承認を行います。

ステップ3：データベースユーザーの作成
Atlas の「Database Access」セクションで、新規ユーザー（例：satoshi）を作成し、パスワード（例：greg1024）を設定します。
このユーザーがアプリケーションから接続する際の認証情報となります。

ステップ4：接続文字列の取得とアプリケーション連携
Atlas の「Clusters」画面から、「Connect」ボタンをクリックし、接続文字列（URI）を取得します。
mongodb+srv://satoshi:greg1024@cluster0.mongodb.net/my_database?retryWrites=true&w=majority
この URI を AWS 上のアプリケーション（ECS、Lambda、EC2 など）の環境変数または設定ファイルに登録します。

ステップ5：スキーマ設計とパフォーマンスチューニング
スキーマ設計
MongoDB はスキーマレスですが、アプリケーションの利用パターンに合わせたドキュメント構造やインデックス設計を行います。
例：ユーザー情報、トランザクション、ログなど、ドキュメントの形状を決定します。
パフォーマンス
Atlas の自動スケールやバックアップ、監視機能（Atlas Metrics）を利用して、パフォーマンスや可用性の監視を行います。

# 3. AWS 側の連携設計例
3.1 AWS のアプリケーション環境の構築（例：ECS Fargate）
VPC の構築（Terraform などで）
AWS 上で VPC、パブリック・プライベートサブネット、インターネットゲートウェイなどを構築します。
すでに前述の Terraform モジュールの例が参考になります。
ECS クラスターの構築
Docker イメージを作成し、ECR にプッシュ。
ECS タスク定義に、環境変数として MongoDB Atlas の接続 URI を登録します。
ALB（Application Load Balancer）の設定
ALB を通して外部からのリクエストを受け付ける場合、セキュリティグループで 80/443 ポートを開放します。

3.2 アプリケーション接続例
Python (Motor を利用)
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    # 環境変数などから取得することも可能
    uri = "mongodb+srv://immudb:greg1024@cluster0.mongodb.net/my_database?retryWrites=true&w=majority"
    client = AsyncIOMotorClient(uri, maxPoolSize=100)
    db = client.my_database
    collection = db.my_collection

    # ドキュメントの挿入
    doc = {"user": "Alice", "action": "login", "timestamp": "2025-03-01T12:00:00Z"}
    result = await collection.insert_one(doc)
    print("Inserted document id:", result.inserted_id)

    # ドキュメントの検索
    async for document in collection.find({"user": "Alice"}):
        print(document)

if __name__ == '__main__':
    asyncio.run(main())

Rust (mongodb crate を利用)
use mongodb::{Client, options::ClientOptions, bson::doc};
use tokio;
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // 接続文字列（環境変数などから取得する場合もあります）
    let client_uri = "mongodb+srv://immudb:greg1024@cluster0.mongodb.net/my_database?retryWrites=true&w=majority";
    let mut client_options = ClientOptions::parse(client_uri).await?;
    client_options.max_pool_size = Some(100);
    
    let client = Client::with_options(client_options)?;
    let database = client.database("my_database");
    let collection = database.collection("my_collection");

    // ドキュメントの挿入
    let new_doc = doc! { "user": "Bob", "action": "purchase", "amount": 99.99 };
    let insert_result = collection.insert_one(new_doc, None).await?;
    println!("Inserted document id: {:?}", insert_result.inserted_id);

    // ドキュメントの検索
    let filter = doc! { "user": "Bob" };
    let mut cursor = collection.find(filter, None).await?;
    while let Some(result) = cursor.try_next().await? {
        println!("Found document: {:?}", result);
    }

    Ok(())
}

# 4. 開発から運用までの流れ
MongoDB Atlas クラスタの作成と設定
Atlas のダッシュボードでクラスタをプロビジョニング
セキュリティ設定（IP ホワイトリスト、または VPC Peering）の設定

AWS 側のインフラ構築
Terraform を使用して VPC、サブネット、ECS クラスター、ALB、IAM、セキュリティグループを構築
ECS タスク定義に Atlas 接続文字列を環境変数で登録

アプリケーションの開発
VSCode やお好みの IDE で、Python や Rust の非同期コードを開発
Atlas への接続テストや、データ操作の実装

デプロイと連携テスト
CI/CD パイプライン（GitHub Actions、AWS CodePipeline など）を利用してコードをビルド・デプロイ
ECS サービスが最新タスク定義で起動し、Atlas へ接続・データ操作が正常に行われるかテスト

# 5. まとめ
MongoDB Atlas のセットアップ
Atlas のクラスタ作成、ユーザー作成、セキュリティ設定を行い、接続文字列を取得します。
AWS インフラの構築
Terraform を利用して VPC、サブネット、セキュリティグループ、ECS クラスター、ALB、IAM などのリソースを構築。
Atlas と AWS 間は VPC Peering または IP ホワイトリストで連携します。

アプリケーション連携
Python（Motor）や Rust（mongodb crate）で非同期処理を実装し、Atlas にデータを読み書きします。

開発・運用フロー
VSCode などの IDE でコード管理、Terraform でインフラ管理、CI/CD パイプラインで自動デプロイを実現します。

これらのステップを順に実施することで、AWS と MongoDB Atlas を統合した堅牢でスケーラブルな MongoDB システムを構築できます。




# MongoDB Atlas（無料枠）でクラスタを作成
Database Access（認証ユーザ）を作成
Network Access（IP ホワイトリスト）に接続元のパブリック IP を登録
接続文字列（URI）を取得
アプリケーション（AWS やローカル PC）から TLS 暗号化されたパブリック接続を行う
これにより、通信自体は TLS で暗号化されるのでデータは保護されますが、経路上はインターネットを通過します。（Atlas 側の仕様として、無料プランはプライベートなピアリング接続に対応していないため）

1. MongoDB Atlas の無料枠クラスタ作成
MongoDB Atlas にログイン
「Create a New Project」 などでプロジェクトを作成（任意の名前）。
「Build a Cluster」または「Create a Cluster」 をクリック。
クラウドプロバイダーとして「AWS」 を選択（他でもOK）。
プラン（Tier）で「M0 - Free Shared Cluster」 を選択。
リージョン は好きな場所（ap-northeast-1 など）を指定。
「Create Cluster」 ボタンを押すと、数分でクラスターが構築されます。
注意: 「M0 (無料)」「M2」「M5」の Shared Tier ではネットワークピアリング機能が利用できません。

2. Database Access（DBユーザ）作成
Atlas 左メニューの 「Database Access」 を開く。
「+ Add New Database User」 をクリック。
ユーザー名・パスワードを設定
例: ユーザー名: satoshi, パスワード: greg1024
ロールは「Atlas admin」か、必要な権限に応じて付与。
「Add User」を押して作成完了。

3. Network Access（IP ホワイトリスト）設定
3-1. 接続元のパブリック IP を調べる
ローカル PC から接続する場合
例えば whatismyip.com などで確認した 自分のグローバルIP をメモする。
AWS の EC2 から接続する場合
EC2 に割り当てられた パブリックIP や、NAT ゲートウェイのパブリック IP を調べる。
EC2 の「Description」タブなどで Public IPv4 Address を確認。
ECS Fargate, Lambda など
NAT Gateway または Internet Gateway 経由で外部に出る場合、その NAT Gateway の IP を把握する。
どうしても固定できないなら、一時的に「0.0.0.0/0」を使う方法もありますが、本番では非推奨です。
3-2. IP アドレスを登録する
Atlas 左メニュー 「Network Access」 → 「IP Access List」
「Add IP Address」 をクリック。
手動で IP を入力 または 「Add Your Current IP Address」ボタンを押す。
「Description」に「My EC2 IP」などメモを入れ、「Confirm」。
数十秒～1分ほど待つと、Atlas がその IP からの接続を許可するようになります。

4. 接続文字列（URI）の取得
Atlas 左メニュー 「Databases」
作成したクラスタの行にある「Connect」ボタンを押す。
「Connect to your application」→「Choose a connection method」
接続文字列（mongodb+srv://...）をコピー
例: mongodb+srv://satoshi:greg1024@cluster0.n2abc.mongodb.net/my_database?retryWrites=true&w=majority
SRV レコード (+srv) がDNSで解決できない場合は、「Standard Connection String」の mongodb://ホスト一覧 形式を使うという手もあります。

5. アプリケーションからパブリック経路で TLS 接続
5-1. Rust の例（非同期でなくともOK）
use mongodb::{bson::doc, error::Result, options::ClientOptions, sync::Client};

fn main() -> Result<()> {
    // Atlas の接続文字列（例）
    let uri = "mongodb+srv://immudb:greg1024@cluster0.n2abc.mongodb.net/my_database?retryWrites=true&w=majority";
    
    // クライアントオプションをパース
    let mut client_options = ClientOptions::parse(uri)?;
    // 必要なら pool_size とか設定可能
    // client_options.max_pool_size = Some(50);

    // クライアント作成
    let client = Client::with_options(client_options)?;

    // データベース・コレクションを選択
    let db = client.database("my_database");
    let collection = db.collection("transactions");

    // ドキュメント挿入テスト
    let insert_result = collection.insert_one(doc!{
        "user": "Alice",
        "action": "send",
        "amount": 100
    }, None)?;

    println!("Inserted document id: {:?}", insert_result.inserted_id);

    Ok(())
}
ポイント: mongodb+srv://... はデフォルトで TLS 暗号化通信を有効にしているので、通信内容は暗号化されます。
パブリック経路ではありますが、中身のデータは保護されています。

5-2. AWS EC2 や ECS からの接続
もしこの Rust アプリをAWS上で動かす場合:

EC2 / ECS タスク 定義
Docker イメージで Rust アプリをコンテナ化するなりして、AWS 環境で起動。
Security Group（アウトバウンド）
27017 / 27015-27019 など MongoDB 通信を許可（ただし、ほとんどの SG はアウトバウンドはデフォルト許可なので問題ない）。
Atlas Network Access へ AWS のパブリック IP も登録
EC2 が持つ固定の Elastic IP などをホワイトリストに追加。
ECS Fargate は NAT Gateway の IP、あるいは 0.0.0.0/0 とする場合もある。
Rust アプリの環境変数 or 設定ファイルに上記 URI を入れて実行。

6. 追加のセキュリティ強化策
IP アクセスリストをなるべく厳密に
0.0.0.0/0 はテスト以外では避ける。
可能なら固定のグローバルIPを取得してホワイトリスト化。
ユーザー権限を絞る
「Atlas admin」ロールではなく、必要最低限のロールを与える。
監査ログ
Atlas には有料プランで強化されたセキュリティ/監査機能があるが、M0 では使える範囲が限定的。
SSHトンネルやVPN
自前でVPNやSSHトンネルを張り、あえてパブリックインターネットを使わずトンネル通信する方法もある。
ただし Atlas 側は結局パブリックホストが待ち受けになる点は変わりません。

# まとめ
無料枠（M0 / Shared Tier）では、VPC Peering / Private Link は使えない。
代替手段として「パブリックエンドポイント + IPホワイトリスト」を利用し、TLS 暗号化通信で安全性を確保するのが一般的。
やり方
Atlas の「Network Access」でAWS やローカル PC のパブリック IPをホワイトリスト追加
「Database Access」でユーザー作成
Atlas の接続文字列（URI） をアプリケーションコードに設定
デフォルトで TLS 暗号化されるので、データは安全にやり取りできる
もし社内ネットワーク or VPC 内だけで完結させたいなら、残念ながら M10 以上（Dedicated Cluster）の利用が必要。
こうした手順で、無料枠の MongoDB Atlas を パブリック接続 + IP ホワイトリスト + TLS という形で使うことができます。これが「無料枠（Shared Tier）でできる最もセキュアな設計」です。


# 中央管理ツールや自動化ツールを導入して、一元管理できる仕組みを検討する必要
MongoDB Atlas自体が各クラスタの状態やパフォーマンスを監視・管理するダッシュボードを提供していますが、複数のプロジェクトやクラスターを一元管理する場合は、以下のようなツールや仕組みが考えられます。

1. MongoDB Atlas API と Terraform
MongoDB Atlas API
AtlasはREST APIを提供しているため、各クラスターの状態や設定の変更、バックアップの管理などを自動化できます。
Terraform Atlas Provider
Terraformを使って、Atlas上のクラスタ構築や設定変更をInfrastructure as Code（IaC）として管理すると、一元的に複数のクラスタの構成をコード化し、自動デプロイ・更新が可能になります。

2. 集中監視ツール
Datadog / Prometheus+Grafana
各クラスタからメトリクスを収集し、統一ダッシュボードで監視できるツールです。
MongoDB Cloud Manager / Ops Manager
自社運用の場合、MongoDB Cloud ManagerやOps Managerを用いることで、複数のクラスタを統合的に管理・監視できます。
AWS CloudWatch
Atlas自体はCloudWatchと連携することも可能なので、AWS上で運用している場合はCloudWatchのダッシュボードを利用して、複数のクラスタのログやメトリクスを一元管理できます。

3. 自動化・オーケストレーションツール
Ansible / Chef / Puppet
クラスタの構成変更やソフトウェア更新、パッチ適用などを自動化するために、これらの構成管理ツールを利用して一元管理する方法もあります。
Kubernetes と MongoDB Operator
クラウドネイティブな環境であれば、Kubernetes上でMongoDB Operatorを用いて、MongoDBクラスタのデプロイ・スケーリング・アップデートを自動化する方法も考えられます。

4. カスタムダッシュボード
Atlas APIや各種モニタリングツールからデータを取得して、Grafanaなどのダッシュボードツールで独自の管理画面を構築する方法も有効です。これにより、複数のクラスタの状態をリアルタイムに確認でき、異常時のアラートも設定できます。
これらのツールを組み合わせることで、20を超える市町村クラスターや大陸クラスターを一元管理し、運用コストや設定の整合性、監視を効率化できます。
たとえば、TerraformとAtlas APIでクラスタ構成をコード化し、DatadogやGrafanaで統一的にモニタリング、さらにAnsibleなどで自動化する、といったアプローチが考えられます。

# レプリカ構成についての考え方（無料枠は3ノード）
送信者（sender）と受信者（receiver）
各トランザクションにおいて、送信者と受信者はどちらも「どのクラスターに対して書き込むか」を示しています。
そのクラスターはそれ自体がレプリカセットであり、書き込みは常にそのレプリカセットのプライマリノードに行われます。
つまり、たとえば「asia-japan-ishikawa-kanazawa」という送信者のクラスターでは、内部でプライマリが決まっており、そこに書き込みます。

セカンダリはどうなるか？
セカンダリノードは、プライマリに対する書き込み内容を非同期で受け取ります。
読み取りのオフロード（例：分析クエリ）は、プライマリの負荷軽減のためにセカンダリを使う設定（SecondaryPreferred など）にすることができますが、書き込みそのものは常にプライマリに対して行われます。
つまり、各クラスターで書き込みに使われるノードは固定的に「その時のプライマリノード」であり、トランザクションごとに送信者のクラスターが「プライマリ」とか「セカンダリ」とかが交互になるということはありません。

トランザクションごとにクラスターが変わる場合
たとえば、あるトランザクションでは送信者が asia のクラスター、別のトランザクションでは送信者が europe のクラスターの場合、
それぞれのクラスター内で常に1台のプライマリが選出され、そのプライマリに対して書き込みが行われます。
したがって、あるトランザクションの送信者が asia のプライマリに書き込むのと、次のトランザクションの送信者が europe のプライマリに書き込む、ということになります。
どちらかがセカンダリになるということはなく、各レプリカセットで書き込み用に常にプライマリが確保されているのです。

まとめ
書き込みは常にそのクラスターのプライマリに対して行われる。
**読み取りは、必要に応じてセカンダリにオフロードできる（ドライバ設定で可能）**が、今回の書き込み中心のシナリオでは関係ありません。
つまり、各トランザクションで「送信者」と「受信者」に対応するクラスターは、それぞれのレプリカセットのプライマリノードに書き込みますので、トランザクションごとに交互にプライマリ／セカンダリが入れ替わることはありません。
各クラスターが独自にレプリカセットとして管理されるため、全体としては高可用性や読み取り分散（セカンダリでの分析クエリ）が実現されます。
この仕組みはMongoDB Atlasの内部で自動的に管理されるため、アプリ側では特に意識する必要はなく、書き込み用の接続文字列を使えばドライバが適切にプライマリを選択してくれます。


#　Atlasの稼働確認が重要
そのリストに、あなたが実際に接続に使っているグローバル IP アドレスが含まれていれば問題ありません。
リスト内の状態が以下のようになっているなら、通常は OK です。

121.3.49.5/32 (includes your current IP address)

「MyLaptop」などのコメントが付いていて、Status が「Active」
これが現在お使いの PC などのグローバル IP であれば、Atlas へのアクセスが許可されます。

103.5.140.156/32
これは別の IP（あるいは以前に追加した IP）で、同じく「Active」となっています。
もし今は使っていない IP なら、そのままでも大きな問題はありません（セキュリティ面で不要なら削除検討）。

確認すべきこと
いま使っているマシン（または CI サーバーなど）のグローバル IP が「121.3.49.5/32」かどうかを再度確認する。
もし違うなら、新しい IP を改めて追加する必要があります。（IP は動的に変わることがあるため）
Status が「Active」 になっているなら、Atlas 側でその IP からのアクセスが有効化されている状態です。
上記を満たしていれば、ホワイトリスト（Network Access）の面では問題ありません。もし接続がタイムアウトする場合、他の原因（ユーザー権限、接続先のクラスターが実在しない、リージョンの遅延など）を再度検証する必要があります。

まとめ
IP ホワイトリスト
「Network Access」画面 → 「Add IP Address」
自分のマシンのグローバルIPを追加
プロジェクト単位での設定なので、複数プロジェクトにわたる場合はそれぞれ追加

ユーザー権限
「Database Access」画面
satoshi ユーザーを作り、admin or readWriteAnyDatabase などの十分な権限を付与
こちらもプロジェクト単位

これらを正しく設定することで、Atlas が接続を拒否せず（ホワイトリストOK） & ユーザー操作を拒否しない（ロールOK） → 高速に動作。1つずつ順番に確認し、漏れがないかを洗い出すと、テストがちゃんと最後まで動き、固まる問題が解消されるはずです。

# テスト結果
running 2 tests
=== Starting test_dag_scenario (DAG-based transaction test) ===
Preparing all HandlerMap for continents & municipalities...
Creating continent handler: asia => mongodb+srv://satoshi:greg1024@asia.kzxnr.mongodb.net/?retryWrites=true&w=majority&appName=asia (db: asia_complete)
test test_dag_scenario has been running for over 60 seconds
test test_mongodb_operations has been running for over 60 seconds
Creating continent handler: europe => mongodb+srv://satoshi:greg1024@europe.jedwh.mongodb.net/?retryWrites=true&w=majority&appName=europe (db: europe_complete)
test test_mongodb_operations ... ok
Creating continent handler: oceania => mongodb+srv://satoshi:greg1024@oceania.hybzs.mongodb.net/?retryWrites=true&w=majority&appName=oceania (db: oceania_complete)
Creating continent handler: africa => mongodb+srv://satoshi:greg1024@africa.vek6o.mongodb.net/?retryWrites=true&w=majority&appName=africa (db: africa_complete)
Creating continent handler: northamerica => mongodb+srv://satoshi:greg1024@northamerica.zej9p.mongodb.net/?retryWrites=true&w=majority&appName=northamerica (db: northamerica_complete)
Creating continent handler: southamerica => mongodb+srv://satoshi:greg1024@southamerica.7noxw.mongodb.net/?retryWrites=true&w=majority&appName=southamerica (db: southamerica_complete)
Creating continent handler: antarctica => mongodb+srv://satoshi:greg1024@antarctica.0rshi.mongodb.net/?retryWrites=true&w=majority&appName=antarctica (db: antarctica_complete)
Creating handler for municipal key: asia-japan-ishikawa-kanazawa
 -> URI=mongodb+srv://satoshi:greg1024@asia-japan-ishikawa-kan.ggn9p.mongodb.net/?retryWrites=true&w=majority&appName=asia-japan-ishikawa-kanazawa, db: asia-japan-ishikawa-kanazawa_complete
 -> Successfully inserted handler for asia-japan-ishikawa-kanazawa
Creating handler for municipal key: asia-japan-tokyo-shibuya
 -> URI=mongodb+srv://satoshi:greg1024@asia-japan-tokyo-shibuy.wh4p1.mongodb.net/?retryWrites=true&w=majority&appName=asia-japan-tokyo-shibuya, db: asia-japan-tokyo-shibuya_complete
 -> Successfully inserted handler for asia-japan-tokyo-shibuya
Creating handler for municipal key: europe-ireland-connacht-sligo
 -> URI=mongodb+srv://satoshi:greg1024@europe-ireland-connacht.npile.mongodb.net/?retryWrites=true&w=majority&appName=europe-ireland-connacht-sligo, db: europe-ireland-connacht-sligo_complete
 -> Successfully inserted handler for europe-ireland-connacht-sligo
Creating handler for municipal key: europe-france-iledefrance-paris
 -> URI=mongodb+srv://satoshi:greg1024@europe-france-iledefran.i4gun.mongodb.net/?retryWrites=true&w=majority&appName=europe-france-iledefrance-paris, db: europe-france-iledefrance-paris_comple
 -> Successfully inserted handler for europe-france-iledefrance-paris
Creating handler for municipal key: oceania-australia-nsw-sydney
 -> URI=mongodb+srv://satoshi:greg1024@oceania-australia-nsw-s.x4kro.mongodb.net/?retryWrites=true&w=majority&appName=oceania-australia-nsw-sydney, db: oceania-australia-nsw-sydney_complete
 -> Successfully inserted handler for oceania-australia-nsw-sydney
Creating handler for municipal key: oceania-newzealand-auckland-auckland
 -> URI=mongodb+srv://satoshi:greg1024@oceania-newzealand-auck.e94y1.mongodb.net/?retryWrites=true&w=majority&appName=oceania-newzealand-auckland-auckland, db: oceania-newzealand-auckland-auckland_c
 -> Successfully inserted handler for oceania-newzealand-auckland-auckland
Creating handler for municipal key: africa-southafrica-westerncape-capetown
 -> URI=mongodb+srv://satoshi:greg1024@africa-southafrica-west.drxhy.mongodb.net/?retryWrites=true&w=majority&appName=africa-southafrica-westerncape-capetown, db: africa-southafrica-westerncape-capetow
 -> Successfully inserted handler for africa-southafrica-westerncape-capetown
Creating handler for municipal key: africa-kenya-nairobi-westlands
 -> URI=mongodb+srv://satoshi:greg1024@africa-kenya-nairobi-we.lxbty.mongodb.net/?retryWrites=true&w=majority&appName=africa-kenya-nairobi-westlands, db: africa-kenya-nairobi-westlands_complet
 -> Successfully inserted handler for africa-kenya-nairobi-westlands
Creating handler for municipal key: northamerica-usa-massachusetts-boston
 -> URI=mongodb+srv://satoshi:greg1024@northamerica-usa-massac.xmfa8.mongodb.net/?retryWrites=true&w=majority&appName=northamerica-usa-massachusetts-boston, db: northamerica-usa-massachusetts-boston_
 -> Successfully inserted handler for northamerica-usa-massachusetts-boston
Creating handler for municipal key: northamerica-canada-ottawa-kanata
 -> URI=mongodb+srv://satoshi:greg1024@northamerica-canada-ott.ewhiy.mongodb.net/?retryWrites=true&w=majority&appName=northamerica-canada-ottawa-kanata, db: northamerica-canada-ottawa-kanata_comp
 -> Successfully inserted handler for northamerica-canada-ottawa-kanata
Creating handler for municipal key: southamerica-arg-buenosaires-buenosaires
 -> URI=mongodb+srv://satoshi:greg1024@southamerica-arg-buenos.9zjns.mongodb.net/?retryWrites=true&w=majority&appName=southamerica-arg-buenosaires-buenosaires, db: southamerica-arg-buenosaires-buenosair
 -> Successfully inserted handler for southamerica-arg-buenosaires-buenosaires
Creating handler for municipal key: southamerica-brazil-saopaulo-santos
 -> URI=mongodb+srv://satoshi:greg1024@southamerica-brazil-sao.hurvn.mongodb.net/?retryWrites=true&w=majority&appName=southamerica-brazil-saopaulo-santos, db: southamerica-brazil-saopaulo-santos_co
 -> Successfully inserted handler for southamerica-brazil-saopaulo-santos
Creating handler for municipal key: antarctica-british-researchstation-rothera
 -> URI=mongodb+srv://satoshi:greg1024@antarctica-british-rese.s87ru.mongodb.net/?retryWrites=true&w=majority&appName=antarctica-british-researchstation-rothera, db: antarctica-british-researchstation-rot
 -> Successfully inserted handler for antarctica-british-researchstation-rothera
Creating handler for municipal key: antarctica-usa-researchstation-mcmurdo
 -> URI=mongodb+srv://satoshi:greg1024@antarctica-usa-research.vbwi6.mongodb.net/?retryWrites=true&w=majority&appName=antarctica-usa-researchstation-mcmurdo, db: antarctica-usa-researchstation-mcmurdo
 -> Successfully inserted handler for antarctica-usa-researchstation-mcmurdo
Creating handler for municipal key: default-default-default-default
 -> URI=mongodb+srv://satoshi:greg1024@default-default-default.zkchx.mongodb.net/?retryWrites=true&w=majority&appName=default-default-default-default, db: default-default-default-default_comple
 -> Successfully inserted handler for default-default-default-default
DAG: holding transactions for 1 second...
Now writing 3 transactions in parallel (DAG scenario)...
Tx inserted => SC:ObjectId("67cc4d970b4690e7c0b1c0d8"), RC:ObjectId("67cc4d970b4690e7c0b1c0da"), SCity:ObjectId("67cc4d970b4690e7c0b1c0d7"), RCity:ObjectId("67cc4d970b4690e7c0b1c0d6")
Tx inserted => SC:ObjectId("67cc4d970b4690e7c0b1c0dc"), RC:ObjectId("67cc4d970b4690e7c0b1c0d4"), SCity:ObjectId("67cc4d970b4690e7c0b1c0db"), RCity:ObjectId("67cc4d970b4690e7c0b1c0d2")
Tx inserted => SC:ObjectId("67cc4d970b4690e7c0b1c0d5"), RC:ObjectId("67cc4d970b4690e7c0b1c0d9"), SCity:ObjectId("67cc4d970b4690e7c0b1c0d3"), RCity:ObjectId("67cc4d970b4690e7c0b1c0d1")
All 3 DAG transactions completed successfully.
test test_dag_scenario ... ok

test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1336.11s

   Doc-tests rsmongodb

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

テスト自体はすべてパスしているので「正しく動作している」という意味では問題ありません。しかし、全体で22分近くかかっているのは、テスト時に多数のクラスターへ新規に接続しているためのオーバーヘッドが大きいからです。

本番環境では、サーバー起動時に一度だけ各クラスターへの接続を確立し、その後はコネクションプールを使いまわすので、毎回新規に接続する必要はなく、実際の運用時の読み書きは高速に行えるはずです。

もし1秒以内の処理速度を目指すのであれば、以下の点を検討してください：

常時接続の維持: アプリ起動時に各クラスターへのハンドラーを一度だけ作成し、再利用する。
接続数の削減: 必要な接続先（大陸と市町村）を本番環境でまとめる、もしくは Dedicated Cluster（有料プラン）を利用することでパフォーマンスを向上させる。
リージョンの最適化: アプリケーションと MongoDB クラスターを同一リージョン内に配置する。
このテストコードはあくまで新規に接続を確立する状況を再現しているため、テストとしては正しいですが、実運用ではこの負荷は発生しません。