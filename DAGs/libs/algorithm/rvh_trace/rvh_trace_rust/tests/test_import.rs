// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\tests\test_import.rs

//! tests/test_import.rs – Python 拡張の「単純 import」チェック
use assert_cmd::Command;
use std::env;
use std::path::PathBuf;

#[test]
fn test_python_import_only() {
    // ── 0. venv の python.exe を使う ────────────────────────────────
    let venv = env::var("VIRTUAL_ENV")
        .expect("run `cargo test` から .venv を有効にして下さい");
    let python = if cfg!(windows) {
        PathBuf::from(&venv).join("Scripts/python.exe")
    } else {
        // Linux/macOS は bin/python または bin/python3
        let cand = ["bin/python", "bin/python3"];
        cand.iter()
            .map(|p| PathBuf::from(&venv).join(p))
            .find(|p| p.exists())
            .expect("python executable not found in venv")
    };

    // ── 1. DLL 検索パスを補完 (…/DLLs; …/) ─────────────────────────
    let dlls  = PathBuf::from(&venv).join("DLLs");
    let mut new_path = env::var_os("PATH").unwrap_or_default();
    let extra = env::join_paths([dlls, PathBuf::from(&venv)]).unwrap();
    new_path.push(";");
    new_path.push(extra);

    // ── 2. PYTHONPATH も venv 内 site-packages を優先 ───────────────
    let site = PathBuf::from(&venv).join("Lib/site-packages");

    // ── 3. サブプロセスで import して終了コード 0 を確認 ──────────
    Command::new(python)
        .arg("-c")
        .arg("import rvh_trace_rust; print('import OK')")
        .env("PATH",      &new_path)
        .env("PYTHONPATH", site)
        .assert()
        .success()
        .stdout(predicates::str::contains("import OK"));
}
