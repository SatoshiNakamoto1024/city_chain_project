// tests/integration_test.rs
use dpos::*; // lib.rs (name="dpos") を参照
use actix_web::{test, App, web};
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc, Duration};

#[actix_rt::test]
async fn test_add_block_handler() {
    // 1) DPoSとDummyChain初期化
    let mut dpos_instance = DPoS::new(); // 変数名を変更
    dpos_instance.update_user_evaluation("Asia-Tokyo-UserX", EvaluationItems {
        total_love_token_usage: 100.0,
        value_from_tokens_received: 50.0,
        contribution_by_token_usage: 30.0,
    });
    // Municipal + Continental reps
    // 例: with_ymd_and_hms(年, 月, 日, 時, 分, 秒)
    let start_date = chrono::Utc.with_ymd_and_hms(2025, 1, 1, 0, 0, 0).unwrap();
    // 失敗する可能性があるので Option を処理
    let end_date   = start_date + chrono::Duration::days(90);
    dpos_instance.select_municipal_representatives("Tokyo", start_date, end_date);
    dpos_instance.select_continental_representatives(start_date, end_date);

    let dummy_chain = DummyChain::new(dpos_instance.clone()); // 変数名を変更

    // 2) Actix用AppState
    let state = AppState {
        chain: Arc::new(Mutex::new(dummy_chain)),
    };

    // 3) テストサーバの準備
    let mut app = test::init_service(
        App::new()
            .app_data(web::Data::new(state.clone()))
            .service(add_block_handler)
            .configure(new_app) // ルートなどを設定する関数
    ).await;

    // 4) リクエスト送信
    let req = test::TestRequest::post()
        .uri("/add_block")
        .set_payload("Hello DPoS block!")
        .to_request();

    let resp = test::call_service(&mut app, req).await;
    assert!(resp.status().is_success(), "Response must be success");

    let body = test::read_body(resp).await;
    let body_str = std::str::from_utf8(&body).unwrap();
    println!("Response: {}", body_str);

    // 5) 追加されたブロックを確認
    let chain_guard = state.chain.lock().unwrap();
    assert_eq!(chain_guard.blocks.len(), 1);
    let first_block = &chain_guard.blocks[0];
    assert!(first_block.approved_by.is_some());
}

#[test]
async fn test_dpos_logic_direct() {
    let mut dpos_instance = DPoS::new(); // 変数名を変更

    // AppState を作成
    let state = AppState {
        chain: Arc::new(Mutex::new(DummyChain::new(dpos_instance.clone()))),
    };
    
    // アプリケーションを初期化
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(state.clone())) // clone して渡す
            .configure(new_app),
    )
    .await;
    
    // テスト用のリクエストを作成
    let req = test::TestRequest::get()
        .uri("/example") // 適切なパスに置き換える
        .to_request();

    // レスポンスを確認
    let resp = test::call_service(&app, req).await;
    assert!(resp.status().is_success());

    dpos_instance.update_user_evaluation("Europe-London-UserA", EvaluationItems {
        total_love_token_usage: 300.0,
        value_from_tokens_received: 100.0,
        contribution_by_token_usage: 120.0,
    });

    let start_date = chrono::Utc.with_ymd_and_hms(2025, 1, 1, 0, 0, 0).unwrap();
    // 失敗する可能性があるため unwrap() を使用

    let end_date   = start_date + chrono::Duration::days(90);

    dpos_instance.select_municipal_representatives("London", start_date, end_date);
    dpos_instance.select_continental_representatives(start_date, end_date);

    let rep_count = dpos_instance.continental_representatives.len();
    assert!(rep_count > 0, "Should have at least 1 continental representative");
    println!("DPoS selected reps: {:?}", dpos_instance.continental_representatives);
}
