// src/lib.rs

use chrono::{DateTime, Utc, Duration};
use std::collections::HashMap;
use actix_web::{web, App, HttpResponse, HttpServer, Responder, get, post};
use std::sync::{Arc, Mutex};

// ---------------------
// 1) データ構造の定義
// ---------------------

/// 評価項目
#[derive(Debug, Clone)]
pub struct EvaluationItems {
    pub total_love_token_usage: f64,
    pub value_from_tokens_received: f64,
    pub contribution_by_token_usage: f64,
}

/// 代表者を表す構造体
#[derive(Debug, Clone)]
pub struct Representative {
    pub user_id: String,
    pub start_date: DateTime<Utc>,
    pub end_date: DateTime<Utc>,
}

/// ダミーのブロック
#[derive(Debug, Clone)]
pub struct Block {
    pub block_id: String,
    pub timestamp: DateTime<Utc>,
    pub data: String,
    pub approved_by: Option<String>, // 誰が承認したか
}

// ---------------------
// 2) 大陸レベルの DPoS
// ---------------------
#[derive(Clone)]
pub struct DPoS {
    pub user_evaluations: HashMap<String, EvaluationItems>,
    pub municipal_representatives: HashMap<String, Vec<Representative>>,
    pub continental_representatives: Vec<Representative>,
    pub approved_representative: Option<String>,
}

#[derive(Clone)]
pub struct AppState {
    pub chain: Arc<Mutex<DummyChain>>, // ArcやMutexもClone可能
    // 他のフィールドも含む
}

async fn get_example() -> impl Responder {
    "Hello, this is /example"
}

pub fn new_app(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::resource("/example")
        .route(web::get().to(get_example))
    );
}

impl DPoS {
    /// コンストラクタ
    pub fn new() -> Self {
        DPoS {
            user_evaluations: HashMap::new(),
            municipal_representatives: HashMap::new(),
            continental_representatives: Vec::new(),
            approved_representative: None,
        }
    }

    /// ユーザー評価を上書き
    pub fn update_user_evaluation(&mut self, user_id: &str, eval: EvaluationItems) {
        self.user_evaluations.insert(user_id.to_string(), eval);
    }

    /// ユーザー評価を加算
    pub fn add_user_evaluation(&mut self, user_id: &str, added: EvaluationItems) {
        let entry = self.user_evaluations.entry(user_id.to_string())
            .or_insert(EvaluationItems {
                total_love_token_usage: 0.0,
                value_from_tokens_received: 0.0,
                contribution_by_token_usage: 0.0,
            });
        entry.total_love_token_usage += added.total_love_token_usage;
        entry.value_from_tokens_received += added.value_from_tokens_received;
        entry.contribution_by_token_usage += added.contribution_by_token_usage;
    }

    /// 市町村IDを引数に、スコア上位5名を選出
    pub fn select_municipal_representatives(
        &mut self,
        municipality_id: &str,
        start_date: DateTime<Utc>,
        end_date: DateTime<Utc>,
    ) {
        let mut user_scores: Vec<(String, f64)> = Vec::new();
        for (user_id, eval) in &self.user_evaluations {
            if user_id.contains(municipality_id) {
                let total_score =
                    eval.total_love_token_usage +
                    eval.value_from_tokens_received +
                    eval.contribution_by_token_usage;
                user_scores.push((user_id.clone(), total_score));
            }
        }

        user_scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        let top_5 = user_scores.into_iter().take(5);

        let reps: Vec<Representative> = top_5
            .collect::<Vec<_>>() // イテレータをVecに変換
            .into_iter() // 再度イテレータに変換
            .map(|(uid, _)| Representative {
                user_id: uid,
                start_date,
                end_date,
            })
            .collect();

        self.municipal_representatives.insert(municipality_id.to_string(), reps);
    }

    /// 大陸代表者を選出
    pub fn select_continental_representatives(
        &mut self,
        start_date: DateTime<Utc>,
        end_date: DateTime<Utc>,
    ) {
        let mut all_candidates: Vec<(String, f64)> = Vec::new();

        for reps in self.municipal_representatives.values() {
            for rep in reps.iter() {
                if let Some(eval) = self.user_evaluations.get(&rep.user_id) {
                    let total_score =
                        eval.total_love_token_usage +
                        eval.value_from_tokens_received +
                        eval.contribution_by_token_usage;
                    all_candidates.push((rep.user_id.clone(), total_score));
                }
            }
        }

        all_candidates.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        self.continental_representatives.clear();
        for (uid, _) in all_candidates.into_iter().take(5) {
            self.continental_representatives.push(Representative {
                user_id: uid,
                start_date,
                end_date,
            });
        }
    }

    /// ブロック承認
    pub fn approve_block(&mut self, block_id: &str) -> Option<String> {
        if self.continental_representatives.is_empty() {
            println!("No continental reps found to approve block.");
            return None;
        }
        if let Some(rep) = self.continental_representatives.get(0) {
            let rep_id = &rep.user_id;
            self.approved_representative = Some(rep_id.clone());
            println!("Block approved by rep_id={}", rep_id);
            Some(rep_id.clone())
        } else {
            println!("No continental reps found to approve block.");
            None
        }
    }
}

/// ダミーチェーン
#[derive(Clone)]
pub struct DummyChain {
    pub blocks: Vec<Block>,
    pub dpos: Arc<Mutex<DPoS>>,
}

impl DummyChain {
    pub fn new(dpos: DPoS) -> Self {
        DummyChain {
            blocks: Vec::new(),
            dpos: Arc::new(Mutex::new(dpos)),
        }
    }

    pub fn add_block(&mut self, data: &str) -> Option<String> {
        let block_id = format!("block-{}", self.blocks.len() + 1);
        let block = Block {
            block_id: block_id.clone(),
            timestamp: Utc::now(),
            data: data.to_string(),
            approved_by: None,
        };
        self.blocks.push(block.clone());

        let mut dpos_guard = self.dpos.lock().unwrap();
        if let Some(rep) = dpos_guard.approve_block(&block_id) {
            if let Some(last) = self.blocks.last_mut() {
                last.approved_by = Some(rep.clone());
            }
            return Some(rep);
        }
        None
    }
}

#[get("/hello")]
async fn hello() -> impl Responder {
    HttpResponse::Ok().body("Hello from DPoS library!")
}

#[post("/add_block")]
async fn add_block_handler(
    data: web::Data<AppState>,
    body: String,
) -> impl Responder {
    let mut chain = data.chain.lock().unwrap();
    let rep_option = chain.add_block(&body);
    match rep_option {
        Some(rep) => HttpResponse::Ok().body(
            format!("Block added & approved by representative: {}", rep)
        ),
        None => HttpResponse::BadRequest().body("No representative found."),
    }
}

#[post("/select_continental_reps")]
async fn select_continental_reps_handler(data: web::Data<AppState>) -> impl Responder {
    let start_date = Utc::now() + Duration::days(90);
    let end_date   = start_date + Duration::days(90);
    let chain = data.chain.lock().unwrap();
    let mut dpos = chain.dpos.lock().unwrap();
    dpos.select_continental_representatives(start_date, end_date);
    HttpResponse::Ok().body("selected continental reps.")
}

/// Actixサーバを起動する関数（テストなどで使用可能）
pub async fn run_server() -> std::io::Result<()> {
    let mut dpos = DPoS::new();
    dpos.update_user_evaluation("Asia-Tokyo-User1", EvaluationItems {
        total_love_token_usage: 500.0,
        value_from_tokens_received: 300.0,
        contribution_by_token_usage: 200.0,
    });

    let local_dpos = dpos.clone(); // ローカル変数として `local_dpos` を定義
    let shared_data = web::Data::new(AppState {
        chain: Arc::new(Mutex::new(DummyChain::new(local_dpos))),
    });

    println!("Starting test server at 127.0.0.1:8088 ...");
    HttpServer::new(move || {
        App::new()
            .app_data(shared_data.clone())
            .service(hello)
            .service(add_block_handler)
            .service(select_continental_reps_handler)
    })
    .bind("127.0.0.1:8088")?
    .run()
    .await
}