// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\tests\test_import.rs
// -------------------------------------------------------------
// 「ビルド済み wheel／editable install 済みの rvh_core_rust を
//  “ただ import できる” ことだけを確認する超軽量テスト」
//
// * Python 実行には “現在の venv” に入っている python.exe を使用
// * Windows では venv 直下の DLLs／ルートを PATH に追加しておく
// * PYTHONPATH は venv の site-packages を先頭に置いておく
//
// 失敗すると「Rust → Python ビルド or インストール」手順に
// 問題があることが分かる。
// -------------------------------------------------------------

use assert_cmd::Command;
use predicates::str::contains;   // ← ★ これを追加
use std::{env, path::PathBuf};

#[test]
fn test_python_import_only() {
    /* --- 0. venv の python.exe ----------------------------------------- */
    let venv = env::var("VIRTUAL_ENV")
        .expect("activate a virtual-env (.venv) before running `cargo test`");
    let python = PathBuf::from(&venv).join(if cfg!(windows) {
        "Scripts/python.exe"
    } else {
        "bin/python"
    });

    /* --- 1. DLL 検索パス (Windows) -------------------------------------- */
    let mut path_var = env::var_os("PATH").unwrap_or_default();
    #[cfg(windows)]
    {
        let dlls = PathBuf::from(&venv).join("DLLs");
        let extra = env::join_paths([dlls, PathBuf::from(&venv)]).unwrap();
        path_var.push(";");
        path_var.push(extra);
    }

    /* --- 2. PYTHONPATH に site-packages を先頭追加 ---------------------- */
    let site_packages = PathBuf::from(&venv).join(if cfg!(windows) {
        "Lib/site-packages"
    } else {
        "lib/python3/site-packages"
    });

    /* --- 3. サブプロセスで import して確認 ------------------------------ */
    Command::new(python)
        .arg("-c")
        .arg("import rvh_core_rust; print('import OK')")
        .env("PATH", &path_var)
        .env("PYTHONPATH", site_packages)
        .assert()
        .success()
        .stdout(contains("import OK"));
}
