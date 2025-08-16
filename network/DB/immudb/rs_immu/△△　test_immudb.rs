// tests/test_immudb.rs
use std::io::ErrorKind;
use std::process::{Command, Child};
use std::path::Path;
use std::thread;
use std::time::Duration;
use tokio::runtime::Runtime;
use rs_immu::ImmuDBClient; // クレートルートから re-export されたクライアント

/// Windows環境でWSLを介してPythonサーバーをspawnする関数
fn spawn_python_server() -> Child {
    // Windows側で WSL を呼び出すための wsl.exe の絶対パス
    let wsl_cmd = "C:\\Windows\\System32\\wsl.exe";
    // 使用するディストリビューション名（例: Ubuntu）
    let distro = "Ubuntu";
    // 仮想環境内の Python インタープリターのパス（WSL上のパス）
    let venv_python = "/home/satoshi/venvs/py_rs_immu_connect/bin/python3";
    // サーバースクリプトの WSL 上のパス（Linux形式）
    let script_path = "/mnt/d/city_chain_project/network/DB/immudb/py_rs_immu_connect/py_rs_immu_server.py";

    // bash を起動し、仮想環境をアクティブにしてからスクリプトを実行する
    let command_line = format!("{} {}", venv_python, script_path);

    let mut command = Command::new(wsl_cmd);
    command.arg("-d")
           .arg(distro)
           .arg("bash")
           .arg("-c")
           .arg(command_line)
           .current_dir("C:\\Windows\\System32");  // ここで明示的に作業ディレクトリを指定

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
        // Pythonサーバーはすべてのインスタンスに対して、単一の gRPC サーバーで待ち受けています
        let server_addr = "http://127.0.0.1:50051";
        let mut client = ImmuDBClient::new(server_addr)
            .await
            .expect("Failed to connect to Python gRPC server");

        // Login："asia"を指定
        let token = client.login("immudb", "greg1024", "asia")
            .await
            .expect("Failed to login");
        println!("Logged in, token: {}", token);
        assert!(!token.is_empty());

        // Set
        let set_resp = client.set_value(&token, "test_key", b"Hello from Rust!")
            .await
            .expect("Failed to set value");
        println!("Set response: success={}, message={}", set_resp.success, set_resp.message);
        assert!(set_resp.success);

        // Get
        let get_resp = client.get_value(&token, "test_key")
            .await
            .expect("Failed to get value");
        if get_resp.success {
            println!("[Rust] Get Success: key={} value={}", "test_key", String::from_utf8_lossy(&get_resp.value));
        } else {
            eprintln!("[Rust] Get Failed: key={}", "test_key");
        }        
        assert!(get_resp.success);
        assert_eq!(
            String::from_utf8_lossy(&get_resp.value),
            "Hello from Rust!"
        );        

        // MultiSet
        let multi_set_resp = client.multi_set(&token, vec![
            ("multi_key1".to_string(), "Value1".to_string()),
            ("multi_key2".to_string(), "Value2".to_string()),
        ])
        .await
        .expect("Failed to perform multi_set");
        println!("MultiSet response: success={}, message={}", multi_set_resp.success, multi_set_resp.message);
        assert!(multi_set_resp.success);

        // Scan
        let scanned = client.scan(&token, "test", false, 10)
            .await
            .expect("Failed to scan");
        println!("Scanned items:");
        for (k, v) in &scanned {
            println!("Key: {}, Value: {}", k, v);
        }
        // test_keyが含まれているはず
        assert!(scanned.iter().any(|(k, _)| k == "test_key"));

        // Logout
        let logout_resp = client.logout(&token)
            .await
            .expect("Failed to logout");
        println!("Logout response: success={}, message={}", logout_resp.success, logout_resp.message);
        assert!(logout_resp.success);
    });

    kill_python_server(&mut python_server);
}
