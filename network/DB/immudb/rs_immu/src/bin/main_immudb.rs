// src/bin/main_immudb.rs

use rs_immu::ImmuDBClient;
use tokio;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // gRPCサーバーのアドレス（Python側の gRPC サーバーがここで起動している）
    // プロキシ設定しているから、このアドレスでOK　test_immudb.rsのアドレスとは異なる。
    let server_addr = "172.31.101.192:50051"; 
    
    // 非同期クライアントの作成
    let mut client = ImmuDBClient::new(server_addr).await?;
    
    // Login: 第三引数として、例えば "asia" を渡す
    let token = client.login("immudb", "greg1024", "asia").await?;
    println!("Logged in, token: {}", token);
    
    // Set: 第1引数は token、次に key, value
    let value = "Hello from Rust!".as_bytes();
    let set_resp = client.set_value(&token, "test_key", value).await?;
    println!("Set response: success={}, message={}", set_resp.success, set_resp.message);
    
    // Get: 第1引数は token、次に key
    let get_resp = client.get_value(&token, "test_key").await?;
    if get_resp.success {
        println!("[Rust] Get Success: key={} value={}", "test_key", String::from_utf8_lossy(&get_resp.value));
    } else {
        eprintln!("[Rust] Get Failed: key={}", "test_key");
    }
    
    // MultiSet: 複数キー・値ペアの設定
    let multi_set_resp = client.multi_set(&token, vec![
        ("multi_key1".to_string(), "Value1".to_string()),
        ("multi_key2".to_string(), "Value2".to_string()),
    ]).await?;
    println!("MultiSet response: success={}, message={}", multi_set_resp.success, multi_set_resp.message);
    
    // Scan: 指定したプレフィックスとリミットでスキャン
    let scanned = client.scan(&token, "test", false, 10).await?;
    println!("Scanned items:");
    for (k, v) in scanned {
        println!("Key: {}, Value: {}", k, v);
    }
    
    // ここに将来、ntru や Dpos、wallet などの処理を組み込む予定です。
    // 例えば、各機能を rs_immu API の呼び出しでラップし、メインチェーン処理に統合するなど

    // Logout
    let logout_resp = client.logout(&token).await?;
    println!("Logout response: success={}, message={}", logout_resp.success, logout_resp.message);
    
    Ok(())
}
