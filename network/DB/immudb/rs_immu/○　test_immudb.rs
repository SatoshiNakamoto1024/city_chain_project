use std::process::{Command, Child};
use std::thread;
use std::time::Duration;
use std::io::ErrorKind;
use tokio::runtime::Runtime;
use tokio::join;
use rs_immu::ImmuDBClient; // クレートルートから re-export されたクライアント

/// Windows環境でWSLを介してPythonサーバーをspawnする関数
/// venvのアクティブ化 → Pythonサーバースクリプトの実行をまとめて行う。
fn spawn_python_server() -> Child {
    // Windows側で WSL を呼び出すための wsl.exe の絶対パス
    // もし PATH で認識されているなら "wsl.exe" だけでもOK。
    // ここではフルパスを指定:
    let wsl_cmd = "C:\\Windows\\System32\\wsl.exe";

    // 使用するディストリビューション名（例: Ubuntu）
    let distro = "Ubuntu";

    // 仮想環境内の Python インタープリターのパス（WSL上のパス）
    let venv_python = "/home/satoshi/venvs/py_rs_immu_connect/bin/python3";

    // サーバースクリプトの WSL 上のパス（Linux形式）
    let script_path = "/mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect/py_rs_immu_server.py";

    // コマンドラインを組み立てる: "python3 /mnt/d/.../py_rs_immu_server.py"
    let command_line = format!("{} {}", venv_python, script_path);

    let mut command = Command::new(wsl_cmd);
    command
        .arg("-d")
        .arg(distro)
        .arg("bash")
        .arg("-c")
        .arg(command_line)
        .current_dir("C:\\Windows\\System32"); // 明示的に作業ディレクトリを指定

    match command.spawn() {
        Ok(child) => child,
        Err(e) => {
            if e.kind() == ErrorKind::NotFound {
                panic!("Failed to spawn Python gRPC server: WSL command '{}' not found", wsl_cmd);
            } else {
                panic!("Failed to spawn Python gRPC server: {}", e);
            }
        }
    }
}

/// スポーンしたPythonサーバーを終了する
fn kill_python_server(child: &mut Child) {
    // 単に kill シグナルを送って終了を待つだけ
    child.kill().expect("Failed to kill Python gRPC server");
    child.wait().expect("Failed to wait on Python gRPC server");
}

#[test]
fn integration_test_immudb_operations() {
    println!("Spawning Python gRPC server from: /mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect/py_rs_immu_server.py");
    let mut python_server = spawn_python_server();
    // サーバー起動待ち（十分な時間、例：10秒）
    thread::sleep(Duration::from_secs(10));

    let rt = Runtime::new().unwrap();
    rt.block_on(async {
        // すべてのインスタンスに対して単一の gRPC サーバーが 0.0.0.0:50051 で待機している
        let server_addr = "http://127.0.0.1:50051";

        // ----------------------------
        // (1) 既存テスト (Asia向け)
        // ----------------------------
        let mut client = ImmuDBClient::new(server_addr)
            .await
            .expect("Failed to connect to Python gRPC server");

        // Login："asia" を指定
        let token = client
            .login("immudb", "greg1024", "asia")
            .await
            .expect("Failed to login");
        println!("Logged in, token: {}", token);
        assert!(!token.is_empty());

        // Set
        let set_resp = client
            .set_value(&token, "test_key", b"Hello from Rust!")
            .await
            .expect("Failed to set value");
        println!("Set response: success={}, message={}", set_resp.success, set_resp.message);
        assert!(set_resp.success);

        // Get
        let get_resp = client
            .get_value(&token, "test_key")
            .await
            .expect("Failed to get value");
        if get_resp.success {
            println!(
                "[Rust] Get Success: key={} value={}",
                "test_key",
                String::from_utf8_lossy(&get_resp.value)
            );
        } else {
            eprintln!("[Rust] Get Failed: key={}", "test_key");
        }
        assert!(get_resp.success);
        assert_eq!(String::from_utf8_lossy(&get_resp.value), "Hello from Rust!");

        // MultiSet
        let multi_set_resp = client
            .multi_set(&token, vec![
                ("multi_key1".to_string(), "Value1".to_string()),
                ("multi_key2".to_string(), "Value2".to_string()),
            ])
            .await
            .expect("Failed to perform multi_set");
        println!("MultiSet response: success={}, message={}", multi_set_resp.success, multi_set_resp.message);
        assert!(multi_set_resp.success);

        // Scan
        let scanned = client
            .scan(&token, "test", false, 10)
            .await
            .expect("Failed to scan");
        println!("Scanned items:");
        for (k, v) in &scanned {
            println!("Key: {}, Value: {}", k, v);
        }
        // "test_key" が含まれているか
        assert!(scanned.iter().any(|(k, _)| k == "test_key"));

        // Logout
        let logout_resp = client
            .logout(&token)
            .await
            .expect("Failed to logout");
        println!("Logout response: success={}, message={}", logout_resp.success, logout_resp.message);
        assert!(logout_resp.success);

        // ----------------------------
        // (2) 4大陸同時テスト
        //     A(asia)->B(europe), C(northamerica)->D(southamerica)
        // ----------------------------

        // (2-1) クライアントを2インスタンス用意 (並行borrow回避のため)
        let mut client_ab = ImmuDBClient::new(server_addr)
            .await
            .expect("Failed to connect for AB transaction");
        let mut client_cd = ImmuDBClient::new(server_addr)
            .await
            .expect("Failed to connect for CD transaction");

        // (2-2) 大陸ごとにログイン
        // A->B
        let token_a = client_ab
            .login("immudb", "greg1024", "asia")
            .await
            .expect("A(asia) login failed");
        let token_b = client_ab
            .login("immudb", "greg1024", "europe")
            .await
            .expect("B(europe) login failed");

        // C->D
        let token_c = client_cd
            .login("immudb", "greg1024", "northamerica")
            .await
            .expect("C(north) login failed");
        let token_d = client_cd
            .login("immudb", "greg1024", "southamerica")
            .await
            .expect("D(south) login failed");

        // (2-3) join! で並行書き込み
        let (res_ab, res_cd) = join!(
            async {
                // A->B 送金 (100harmony)
                let resp_a_send = client_ab
                    .set_value(
                        &token_a,
                        "Tx_A->B",
                        b"A(asia, Kanazawa) -> B(europe, Paris): 100harmony tokens"
                    )
                    .await?;
                println!("(A->B) Asia DB set: success={}, message={}", resp_a_send.success, resp_a_send.message);

                let resp_b_recv = client_ab
                    .set_value(
                        &token_b,
                        "Tx_A->B",
                        b"B(europe, Paris) received 100harmony tokens from A(asia, Kanazawa)"
                    )
                    .await?;
                println!("(A->B) Europe DB set: success={}, message={}", resp_b_recv.success, resp_b_recv.message);

                Ok::<(), Box<dyn std::error::Error>>(())
            },
            async {
                // C->D 送金 (300harmony)
                let resp_c_send = client_cd
                    .set_value(
                        &token_c,
                        "Tx_C->D",
                        b"C(northamerica, NY) -> D(southamerica, SaoPaulo): 300harmony tokens"
                    )
                    .await?;
                println!("(C->D) North DB set: success={}, message={}", resp_c_send.success, resp_c_send.message);

                let resp_d_recv = client_cd
                    .set_value(
                        &token_d,
                        "Tx_C->D",
                        b"D(southamerica, SaoPaulo) received 300harmony tokens from C(northamerica, NY)"
                    )
                    .await?;
                println!("(C->D) South DB set: success={}, message={}", resp_d_recv.success, resp_d_recv.message);

                Ok::<(), Box<dyn std::error::Error>>(())
            }
        );

        // エラーチェック
        if let Err(e) = res_ab {
            panic!("A->B transaction failed: {}", e);
        }
        if let Err(e) = res_cd {
            panic!("C->D transaction failed: {}", e);
        }

        // (2-4) Get して確認
        let ab_a_get = client_ab
            .get_value(&token_a, "Tx_A->B")
            .await
            .expect("Get Tx_A->B from Asia DB failed");
        let ab_b_get = client_ab
            .get_value(&token_b, "Tx_A->B")
            .await
            .expect("Get Tx_A->B from Europe DB failed");

        let cd_c_get = client_cd
            .get_value(&token_c, "Tx_C->D")
            .await
            .expect("Get Tx_C->D from North DB failed");
        let cd_d_get = client_cd
            .get_value(&token_d, "Tx_C->D")
            .await
            .expect("Get Tx_C->D from South DB failed");

        println!("\n(A->B) Asia DB: {}", String::from_utf8_lossy(&ab_a_get.value));
        println!("(A->B) EuropeDB: {}", String::from_utf8_lossy(&ab_b_get.value));
        println!("(C->D) North DB: {}", String::from_utf8_lossy(&cd_c_get.value));
        println!("(C->D) South DB: {}", String::from_utf8_lossy(&cd_d_get.value));

        // いちおう成功確認
        assert!(ab_a_get.success);
        assert!(ab_b_get.success);
        assert!(cd_c_get.success);
        assert!(cd_d_get.success);

        // ログアウト
        let out_a = client_ab.logout(&token_a).await.expect("Failed logout(A)");
        let out_b = client_ab.logout(&token_b).await.expect("Failed logout(B)");
        let out_c = client_cd.logout(&token_c).await.expect("Failed logout(C)");
        let out_d = client_cd.logout(&token_d).await.expect("Failed logout(D)");

        assert!(out_a.success && out_b.success && out_c.success && out_d.success);
        println!("\n=== 4大陸同時テスト完了 ===");
    });

    kill_python_server(&mut python_server);
}
