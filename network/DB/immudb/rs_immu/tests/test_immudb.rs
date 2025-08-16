use std::process::{Command, Child};
use std::io::ErrorKind;
use std::time::Duration;
use std::thread;

fn spawn_python_server() -> Child {
    let wsl_cmd = "C:\\Windows\\System32\\wsl.exe";  // or just "wsl.exe" if in PATH
    let distro = "Ubuntu";

    // venv python3
    let venv_python = "/home/satoshi/venvs/py_rs_immu_connect/bin/python3";
    // サーバースクリプト
    let script_path = "/mnt/d/city_chain_project/network/DB/immudb/py_immu_connect/py_rs_immu_server.py";

    let command_line = format!("{} {}", venv_python, script_path);

    let mut command = Command::new(wsl_cmd);
    command.arg("-d")
        .arg(distro)
        .arg("bash")
        .arg("-c")
        .arg(command_line);

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

fn kill_python_server(child: &mut Child) {
    child.kill().expect("Failed to kill Python gRPC server");
    child.wait().expect("Failed to wait on Python gRPC server");
}

use rs_immu::ImmuDBClient;
use tokio::runtime::Runtime;
use tokio::join;
use futures::stream::{FuturesUnordered, StreamExt};

/// 超並列テスト：複数タスクで immudb に書き込みを行う
async fn parallel_set_get(
    client: &mut ImmuDBClient,
    token: &str,
    prefix: &str,
    count: usize,
) -> Result<(), Box<dyn std::error::Error>> {
    let mut tasks = FuturesUnordered::new();

    for i in 0..count {
        // clone() が使えない場合は別の方法（複数クライアント生成など）を検討
        let mut c = client.clone();
        let tok = token.to_string();
        let key_str = format!("{}-key-{}", prefix, i);
        let val_str = format!("{}-val-{}", prefix, i);

        tasks.push(async move {
            // 1) Set
            c.set_value(&tok, &key_str, val_str.as_bytes()).await?;
            // 2) Get
            let getr = c.get_value(&tok, &key_str).await?;
            if getr.success {
                let val_got = String::from_utf8_lossy(&getr.value);
                if val_got != val_str {
                    eprintln!("Mismatch: key={}, expected={}, got={}", key_str, val_str, val_got);
                }
            } else {
                eprintln!("Get fail: key={}", key_str);
            }
            Ok::<(), Box<dyn std::error::Error>>(())
        });
    }

    while let Some(res) = tasks.next().await {
        if let Err(e) = res {
            eprintln!("Task error: {}", e);
        }
    }
    Ok(())
}

#[test]
fn integration_test_immudb_operations() {
    println!("[TEST] Spawning Python gRPC server...");
    let mut py_server = spawn_python_server();

    // サーバー起動待ち (10秒)
    thread::sleep(Duration::from_secs(10));

    let rt = Runtime::new().unwrap();
    rt.block_on(async {
        let server_addr = "http://127.0.0.1:50051";
        let mut client = ImmuDBClient::new(server_addr)
            .await
            .expect("Failed to connect to py gRPC server");

        // (A) 単純テスト (Asia)
        let token = client.login("immudb", "greg1024", "asia")
            .await
            .expect("Fail login(asia)");
        println!("Logged in (asia): token={}", token);

        // Set -> Get
        let set_resp = client.set_value(&token, "test_key", b"Hello from Rust concurrency!")
            .await
            .expect("Fail set");
        assert!(set_resp.success);

        let get_resp = client.get_value(&token, "test_key")
            .await
            .expect("Fail get");
        assert!(get_resp.success);
        println!("(asia) get => {}", String::from_utf8_lossy(&get_resp.value));

        // (B) 大量並列書き込みテスト
        parallel_set_get(&mut client, &token, "asia-bulk", 100).await
            .expect("Fail parallel test(asia)");
        println!("[TEST] parallel_set_get(asia, 100) done");

        // Logout
        let logout_resp = client.logout(&token)
            .await
            .expect("Fail logout");
        assert!(logout_resp.success);

        // (C) 4大陸同時に並列書き込みテスト
        let mut client_asia = ImmuDBClient::new(server_addr).await.unwrap();
        let mut client_eu = ImmuDBClient::new(server_addr).await.unwrap();
        let mut client_na = ImmuDBClient::new(server_addr).await.unwrap();
        let mut client_sa = ImmuDBClient::new(server_addr).await.unwrap();

        let tok_asia = client_asia.login("immudb", "greg1024", "asia").await.unwrap();
        let tok_eu = client_eu.login("immudb", "greg1024", "europe").await.unwrap();
        let tok_na = client_na.login("immudb", "greg1024", "northamerica").await.unwrap();
        let tok_sa = client_sa.login("immudb", "greg1024", "southamerica").await.unwrap();

        let (r_asia, r_eu, r_na, r_sa) = join!(
            parallel_set_get(&mut client_asia, &tok_asia, "A_multi", 50),
            parallel_set_get(&mut client_eu,   &tok_eu,   "B_multi", 50),
            parallel_set_get(&mut client_na,   &tok_na,   "C_multi", 50),
            parallel_set_get(&mut client_sa,   &tok_sa,   "D_multi", 50),
        );
        r_asia.unwrap();
        r_eu.unwrap();
        r_na.unwrap();
        r_sa.unwrap();
        println!("[TEST] 4-continents parallel test done");

        let _ = client_asia.logout(&tok_asia).await;
        let _ = client_eu.logout(&tok_eu).await;
        let _ = client_na.logout(&tok_na).await;
        let _ = client_sa.logout(&tok_sa).await;
    });

    kill_python_server(&mut py_server);
}
