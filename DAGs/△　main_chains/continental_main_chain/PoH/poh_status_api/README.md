以下に、PoHの状態を取得するAPIをモジュール化した例を示します。
ここではファイル名を poh_status_api.rs とし、外出しして main_chain（continental_main_chainなど）から呼び出す想定にしています。

モジュール側(poh_status_api.rs)では、以下を行います:

AppState (PoHを内包している状態) のスコープにアクセスできるように crate:: や use crate::AppState; といった形で参照します。
#[get("/poh_status")] ルートハンドラを定義し、PoHの最新ハッシュ・イベント数・履歴一覧を返す
また、テスト用トランザクションに関しては省略せず、「それがどのように AppState や PoH に関わるか」もあわせて記載しています。

poh_status_api.rs の全文（修正前）
rust
// -----------------------------------------------------------------------
// ファイル名: poh_status_api.rs
// -----------------------------------------------------------------------
use rocket::{get, serde::json::Json, State};
use rocket::serde::json::Value;
use std::sync::Arc;
use tokio::sync::Mutex;

// --- crate 内に定義された AppState や ProofOfHistory を参照する想定 ---
use crate::{AppState, Transaction};  // 適宜、別ファイルで定義している AppState, Transaction のパスに合わせる

/// PoH状態を取得するためのAPIエンドポイント。
/// 
/// - 最新ハッシュ (latest_hash)
/// - PoHに保持されているイベント数 (count)
/// - イベント履歴 (events)
#[get("/poh_status")]
pub async fn get_poh_status(state: &State<Arc<Mutex<AppState>>>) -> Json<Value> {
    // State(AppState)のロックを取得
    let state_guard = state.lock().await;
    // AppState内にある poh: Arc<Mutex<ProofOfHistory>> を参照
    let mut poh_guard = state_guard.poh.lock().await;

    // 現在のPoHのイベント履歴や最新ハッシュなどを取得
    let events = poh_guard.get_events();           // 全イベントの一覧 (Vec<String>)
    let latest = poh_guard.get_latest_hash().to_string();
    let count = poh_guard.len();                   // イベント数

    // JSON形式で返す (例: {"latest_hash": "...", "count": 123, "events": [...]})
    Json(serde_json::json!({
        "latest_hash": latest,
        "count": count,
        "events": events,
    }))
}
注: crate::AppState は、main_chain 側で以下のように定義されていると想定してください:

rust
pub struct AppState {
    // ...
    pub poh: Arc<Mutex<ProofOfHistory>>,
    // ...
}
ProofOfHistory は、たとえば:

rust
pub struct ProofOfHistory {
    sequence: VecDeque<String>,
    current_hash: String,
}

impl ProofOfHistory {
    pub fn new() -> Self { ... }
    pub fn add_event(&mut self, event_str: &str) { ... }
    pub fn get_latest_hash(&self) -> &str { ... }
    pub fn get_events(&self) -> Vec<String> { ... }
    pub fn len(&self) -> usize { ... }
}
のようなイメージです。

main_chain での使用例
continental_main_chain (あるいは main_chain.rs など) においては、poh_status_api モジュールを mod で読み込み、ルートへマウントすればOKです。
以下は抜粋例です。

rust
// -----------------------------------------------------------------------
// ファイル: main_chain.rs (例)
// -----------------------------------------------------------------------
#[macro_use] extern crate rocket;  // ルートマクロ用
use rocket::fairing::AdHoc;
use rocket::{Rocket, Build};

use std::sync::Arc;
use tokio::sync::Mutex;

// ---- 外部モジュールをここで use ----
mod poh_status_api; // 先ほどのファイル (poh_status_api.rs)
use poh_status_api::get_poh_status;

// ---- このチェーンで使う AppState / Transaction / ProofOfHistory ----
pub struct AppState {
    pub poh: Arc<Mutex<ProofOfHistory>>,
    // ...他にも pending_transactions, dpos など
}

pub struct Transaction {
    sender: String,
    receiver: String,
    amount: f64,
    // ...略...
}

pub struct ProofOfHistory {
    // ...略...
}

// Rocketの起動
#[rocket::main]
async fn main() -> Result<(), rocket::Error> {
    // PoHを初期化した AppState を作る
    let poh = Arc::new(Mutex::new(ProofOfHistory::new()));
    let app_state = AppState {
        poh,
        // ...
    };
    let shared_state = Arc::new(Mutex::new(app_state));

    // Rocket のビルド
    let _ = rocket::build()
        .manage(shared_state)           // Arc<Mutex<AppState>>を注入
        .mount("/", routes![
            // ...ほかのルート
            get_poh_status,            // ここでPoH閲覧のAPIをマウント
        ])
        .attach(AdHoc::on_liftoff("Liftoff", |_| {
            Box::pin(async move {
                println!("Continental main chain is live!");
            })
        }))
        .launch()
        .await?;

    Ok(())
}
参考: テスト用トランザクションの例
質問文中にあるテスト用 Transaction 作成例です。
PoHを使うのであれば、トランザクション受信や承認のたびに poh.add_event(...) を呼び出して時系列を証明します。

rust
// テスト用トランザクションを挿入する例
// (たとえば main_chain の何らかの関数内で)

let test_transaction = Transaction::new(
    "Alice".to_string(),
    "Bob".to_string(),
    100.0,
    "VerifiableCredential".to_string(),
    "dummy_signature".to_string(),
    (35.0, 139.0),
    "subject".to_string(),
    "action_level".to_string(),
    "dimension".to_string(),
    "fluctuation".to_string(),
    "organism_name".to_string(),
    "details".to_string(),
    "goods_or_money".to_string(),
    "send".to_string(),
    "Asia-Tokyo".to_string(),
    "Europe-London".to_string(),
    "Asia".to_string(),
    "Europe".to_string(),
    "pending".to_string(), // ステータスを "pending" に設定
    chrono::Utc::now(),
    "sender_municipal_id".to_string(),
    "receiver_municipal_id".to_string(),
    // attributes
    {
        let mut map = std::collections::HashMap::new();
        map.insert("project_id".to_string(), "12345".to_string());
        map.insert("description".to_string(), "テスト用トランザクション".to_string());
        map
    },
);

// たとえば PoH に記録 (受信した、とか)
{
    let mut state_guard = shared_state.lock().await; 
    let mut poh_guard = state_guard.poh.lock().await;
    let event_str = format!("ReceiveTx: {}, from {} -> {} at {}",
                            test_transaction.transaction_id,
                            test_transaction.sender,
                            test_transaction.receiver,
                            chrono::Utc::now());
    poh_guard.add_event(&event_str);
}
このように、トランザクション受信（または作成）とともに、PoHイベントとして記録しておけば、**後から「いつ受理したか」**をチェーン上で証明できます。

以上で、「PoHの状態を取得するAPIをモジュール化した例」および「それを main_chain などで使用する流れ」とテスト用トランザクションを含めたコード全体の例となります。



// PoHイベントとして記録しておけば、**後から「いつ受理したか」**をチェーン上で証明できます。
こうして記録されたイベントが、poh_status_api.rsにて参照できるという事ね。では、もっと具体的にこの履歴を用いていつ受信したのかを証明する用途にすぐに使えるように、poh_status_api.rsの全文を修正してやりなおしてみる。

以下は、PoHの状態を取得するAPIをより具体的に実装した例です。
いつ受信したのかを証明するために、PoHが内部でイベントごとに

イベント文字列（event_str）
記録日時（recorded_at）
ハッシュ（event_hash）
を管理しているとします。そのうえで、poh_status_api に履歴全体と各イベントの詳細をJSON形式で返却するエンドポイントを実装します。

1. poh_status_api\src\lib.rs全文（修正後）
// -----------------------------------------------------------------------
// ファイル名: lib.rs
// -----------------------------------------------------------------------
use rocket::{get, serde::json::Json, State};
use rocket::serde::json::Value;
use std::sync::Arc;
use tokio::sync::Mutex;
use chrono::Utc;

// crate 内で定義されている AppState, ProofOfHistory, PoHEvent を use する想定
use crate::{AppState, PoHEvent};

/// PoHの状態 (最新ハッシュ・イベント数・各イベントの詳細) を返すAPI.
///
/// - `latest_hash`: 直近のPoHハッシュ
/// - `count`: PoHに記録されているイベント数
/// - `events`: イベントのリスト（イベント文字列、記録日時、イベントハッシュ）
#[get("/poh_status")]
pub async fn get_poh_status(state: &State<Arc<Mutex<AppState>>>) -> Json<Value> {
    // AppStateのロックを取得
    let state_guard = state.lock().await;
    // AppStateのPoHロックを取得
    let poh_guard = state_guard.poh.lock().await;

    // イベント一覧を取得
    let events_detail = poh_guard.get_events_detail();  // 例: Vec<PoHEvent>
    // 最新ハッシュの取得
    let latest = poh_guard.get_latest_hash().to_string();
    // イベント数
    let count = poh_guard.len();

    // イベントをJSON配列に変換
    // (event_str, recorded_at, event_hash)をまとめて返す
    let events_json: Vec<Value> = events_detail.iter().map(|ev| {
        serde_json::json!({
            "event_str": ev.event_str,
            "recorded_at": ev.recorded_at.to_rfc3339(),
            "event_hash": ev.event_hash
        })
    }).collect();

    // JSON形式で返す
    Json(serde_json::json!({
        "latest_hash": latest,
        "count": count,
        "events": events_json,
    }))
}
ポイント

poh_guard.get_events_detail() で、イベント情報（PoHEvent）のリストを取得していると仮定
PoHEvent には event_str（例: "ReceiveTx: ..."）、recorded_at（DateTime<Utc>）、event_hash（イベントごとのハッシュ）を持たせる
2. AppState と ProofOfHistory の例
こちらはあくまで参考になります。あなたのプロジェクトの構成に合わせて、
poh_status_api と同じクレート/モジュール内で参照できるようにしてください。

rust
// -----------------------------------------------------------------------
// 例: main_chain.rs などにある AppState, ProofOfHistory, PoHEvent
// -----------------------------------------------------------------------
use std::collections::VecDeque;
use std::sync::Arc;
use tokio::sync::Mutex;
use chrono::{DateTime, Utc};
use sha2::{Sha256, Digest};
use hex;

pub struct AppState {
    pub poh: Arc<Mutex<ProofOfHistory>>, 
    // ...他にも pending_transactions や DPoS などを持っているかもしれません
}

/// イベント1件分の情報
pub struct PoHEvent {
    pub event_str: String,         // イベント内容 (例: "ReceiveTx: ..., from=..., to=..., at=...")
    pub recorded_at: DateTime<Utc>,// このイベントがPoHに記録されたUTC日時
    pub event_hash: String,        // イベントごとのハッシュ
}

/// シンプルなPoH構造体
pub struct ProofOfHistory {
    pub sequence: VecDeque<PoHEvent>,  // イベントのリスト
    pub latest_hash: String,           // 現状のPoHハッシュ(連鎖ハッシュ)
}

impl ProofOfHistory {
    /// 新規作成
    pub fn new() -> Self {
        ProofOfHistory {
            sequence: VecDeque::new(),
            latest_hash: String::new(), // 初期は空文字列など
        }
    }

    /// イベントを追加する
    pub fn add_event(&mut self, event_str: &str) {
        let now = Utc::now();

        // イベント文字列と現在時刻から、個々のイベントハッシュを生成
        let mut hasher = Sha256::new();
        // 前回の latest_hash, 現在の event_str, 時刻等を連結してハッシュ
        hasher.update(self.latest_hash.as_bytes());
        hasher.update(event_str.as_bytes());
        hasher.update(now.to_rfc3339().as_bytes());

        let event_hash = hex::encode(hasher.finalize());

        // PoHEventを作成
        let ev = PoHEvent {
            event_str: event_str.to_string(),
            recorded_at: now,
            event_hash: event_hash.clone(),
        };

        // sequenceにpush
        self.sequence.push_back(ev);
        // latest_hashを更新（PoH連鎖用のハッシュ更新）
        self.latest_hash = event_hash;
    }

    /// イベントの詳細を取得 (Vec<PoHEvent>)
    pub fn get_events_detail(&self) -> Vec<PoHEvent> {
        self.sequence.iter().cloned().collect()
    }

    /// 直近のハッシュを取得
    pub fn get_latest_hash(&self) -> &str {
        &self.latest_hash
    }

    /// イベント数
    pub fn len(&self) -> usize {
        self.sequence.len()
    }
}
解説

add_event(&mut self, event_str: &str) を呼び出すたびに、PoHEvent が作成され、sequence 末尾に格納
latest_hash は、前回のlatest_hashと新イベント内容・時刻などを連結して計算
get_events_detail() で Vec<PoHEvent> を返せば、 poh_status_api.rs の get_poh_status() 内で参照できます
3. 実際のトランザクション受信時のイベント記録例
たとえば、トランザクションを受信した際にPoHにイベントを追加するには、次のようにします:

rust
// たとえば main_chain.rs の中でトランザクションを受信したあと
// "いつ受信したか" をPoHに記録する例

{
    let mut state_guard = shared_state.lock().await;     // AppStateのロック
    let mut poh_guard = state_guard.poh.lock().await;    // PoHのロック

    // event_strを組み立て
    let event_str = format!(
        "ReceiveTx: {}, from={} -> {} at={}",
        test_transaction.transaction_id,
        test_transaction.sender,
        test_transaction.receiver,
        chrono::Utc::now().to_rfc3339() // 受信した瞬間の時刻
    );
    poh_guard.add_event(&event_str);
}

// → この結果、PoHに "ReceiveTx: ..." が追加され、
//    latest_hash も更新される。
//    あとで /poh_status を叩けば、
//    events配列にこのイベントが含まれている。
こうしてイベントを都度PoHに記録しておけば、
GET /poh_status で以下のような履歴が取得できます:

json
{
  "latest_hash": "2a5fcda50f66...",
  "count": 1,
  "events": [
    {
      "event_str": "ReceiveTx: 1234..., from=Alice -> Bob at=2024-12-28T12:34:56Z",
      "recorded_at": "2024-12-28T12:34:56Z",
      "event_hash": "2a5fcda50f66..."
    }
  ]
}
このイベントハッシュと連鎖ハッシュ（latest_hash）を使うことで、
「いつ（recorded_at）」「どんなイベント内容（event_str）」「どんなハッシュ連鎖（event_hash）で改ざん防止しているか」を証明できます。

4. 動作イメージ
どこかの処理でトランザクションを受信
poh_guard.add_event("ReceiveTx: ...") でPoHに記録
/poh_status エンドポイントにアクセスすると、PoHの最新状態を参照可能
こうして「いつ受理したのか」を、PoHのイベント履歴から取得・確認できます。
改ざんが行われれば連鎖ハッシュ (latest_hash や各 event_hash) が変わるため、履歴の正当性を担保できます。





