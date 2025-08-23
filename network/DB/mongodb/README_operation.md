推奨スキーマ（最初から将来対応できる形）

例：送金／行動ログ系コレクション tx_events

{
  "_id": "...",
  "continent": "AS",          // 大陸: AS/EU/NA/SA/AF/OC/AN など
  "country_code": "JP",
  "pref_code": "17",          // 県（石川なら 17）
  "city_code": "17204",       // 例：加賀市など JIS/自治体コード
  "municipality": "Kaga",
  "timestamp": 1733392000,    // epoch秒（HLCも可）
  "tx_type": "send_pending",  // 状態
  "amount": 123.45,
  "...": "その他メタ"
}

# まず作るべきインデックス
地域単位での参照が多い：
({ continent: 1, country_code: 1, pref_code: 1, city_code: 1, timestamp: -1 })

大陸・国・時間帯での分析：
({ continent: 1, country_code: 1, timestamp: -1 })

期限切れ削除（保留6ヶ月など）：
TTL インデックス（expireAt フィールド or timestamp + expireAfterSeconds）

将来シャーディングする際は、シャードキー候補を
continent, country_code, timestamp（複合）あたりで設計しておくと移行が楽です
（ゾーンシャーディングで大陸＝ゾーンに寄せる、時間で分散など）。

# 無料枠（M0）での具体的な進め方
1) 7大陸 × 1クラスターを用意
Atlas で Project を「world」1つでもよし、大陸ごとに Projectを分けてもOK（権限や課金分離を考えるなら後者）。
各大陸に最寄りリージョンで M0 を1個ずつ作成（※M0は地域選択に制限があるので、近接リージョンでも可）。
それぞれ DB User（読み書き専用）と IP allow を設定。

2) 接続の切り替えロジック（アプリ側）
「どのクラスターに書くか/読むか？」を大陸キーでルーティング。
.env を 大陸→URI のマップにして、送受信・分析で呼び分ける。
.env（例）
MONGODB_URL_AS="mongodb+srv://...ap-northeast-1..."
MONGODB_URL_EU="mongodb+srv://...eu-west-1..."
MONGODB_URL_NA="mongodb+srv://...us-east-1..."
...

・Python 例（大陸でルーティング）
import os
from motor.motor_asyncio import AsyncIOMotorClient

URLS = {
    "AS": os.getenv("MONGODB_URL_AS"),
    "EU": os.getenv("MONGODB_URL_EU"),
    "NA": os.getenv("MONGODB_URL_NA"),
    "SA": os.getenv("MONGODB_URL_SA"),
    "AF": os.getenv("MONGODB_URL_AF"),
    "OC": os.getenv("MONGODB_URL_OC"),
    "AN": os.getenv("MONGODB_URL_AN"),
}

def get_db_by_continent(continent: str, dbname: str):
    url = URLS[continent]
    client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
    return client[dbname]

・Rust 例（環境変数で取り分け）
use mongodb::{Client, options::ClientOptions};
use std::env;

pub async fn db_for_continent(cont: &str, dbname: &str) -> mongodb::error::Result<mongodb::Database> {
    let key = format!("MONGODB_URL_{}", cont);
    let url = env::var(key).expect("missing env for continent");
    let opts = ClientOptions::parse(url).await?;
    let client = Client::with_options(opts)?;
    Ok(client.database(dbname))
}

これで 送信系は所属大陸へ直書き、受信系/分析系は必要な大陸に読み分け が可能。
無料枠ではクロスクエリはできないので、アプリ層で集約します（下の“グローバル分析”参照）。

3) コレクションの切り方（論理分割）
DBは大陸単位（例：city_chain_asia）、コレクションで機能別（tx_events, journal_entries など）。
国・県・市町村はフィールドで持たせ、上記の複合インデックスで高速化。
Free枠の容量/コネクション数は非常に小さいため、テスト用のサブセットで運用するのがコツ。