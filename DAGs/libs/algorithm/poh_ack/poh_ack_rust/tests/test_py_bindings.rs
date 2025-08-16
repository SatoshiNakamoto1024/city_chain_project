// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\tests\test_py_bindings.rs
//! PoH-ACK  Python バインディング smoke-test
//! cargo test --features python-embed で実行

use pyo3::prelude::*;
use pyo3::types::PyList;
use std::{env, fs, path::PathBuf};
use walkdir::WalkDir;

/* ── OS ごとの共有ライブラリ拡張子 ─────────────────────────── */
#[cfg(target_os = "windows")]
const DLL_EXT: &str = "dll";
#[cfg(target_os = "macos")]
const DLL_EXT: &str = "dylib";
#[cfg(target_os = "linux")]
const DLL_EXT: &str = "so";

/* ── テストが許容する拡張子（ビルド形態で揺れる） ─────────────── */
#[cfg(target_os = "windows")]
const CAND_EXT: &[&str] = &["dll", "pyd"]; // embed と pyo3/extension-module
#[cfg(target_os = "macos")]
const CAND_EXT: &[&str] = &["dylib"];
#[cfg(target_os = "linux")]
const CAND_EXT: &[&str] = &["so"];

/* ── 0. `target` ルート候補を列挙 ───────────────────────────── */
fn candidate_target_roots() -> Vec<PathBuf> {
    let mut v = Vec::new();

    // (a) CARGO_TARGET_DIR があれば最優先
    if let Ok(d) = env::var("CARGO_TARGET_DIR") {
        v.push(PathBuf::from(d));
    }

    // (b) クレートローカル <crate>/target（従来パス）
    v.push(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("target"));

    // (c) ancestors を順番にたどり、直下に target/ があるものを全部追加
    for anc in PathBuf::from(env!("CARGO_MANIFEST_DIR")).ancestors() {
        let t = anc.join("target");
        if t.is_dir() { v.push(t); }
    }

    v
}

/* ── 1. Python 用 cdylib / pyd を探す ─────────────────────── */
fn find_cdylib() -> PathBuf {
    for root in candidate_target_roots() {
        for profile in ["debug", "release"] {
            for sub in ["", "deps"] {
                let dir = root.join(profile).join(sub);
                if !dir.is_dir() {
                    continue;
                }
                for entry in WalkDir::new(&dir).max_depth(1).into_iter().flatten() {
                    let p = entry.path();
                    let ext = p.extension().and_then(|e| e.to_str()).unwrap_or("");
                    if !CAND_EXT.contains(&ext) {
                        continue;
                    }
                    let stem = p.file_stem().and_then(|s| s.to_str()).unwrap_or("");
                    let name = stem.trim_start_matches("lib"); // *nix は libpoh_ack_rust.so
                    if name.starts_with("poh_ack_rust") {
                        return p.to_path_buf();
                    }
                }
            }
        }
    }
    panic!(
        "poh_ack_rust の共有ライブラリが見つかりません。\
         `cargo build --features python`（.pyd）か \
         `cargo build --features python-embed`（.dll）を実行してください。"
    );
}

/* ── 2. Windows なら .dll → .pyd へコピー ─────────────────── */
#[cfg(target_os = "windows")]
fn ensure_pyd(dll: &PathBuf) -> PathBuf {
    let pyd = dll.with_extension("pyd");
    if !pyd.exists() {
        fs::copy(dll, &pyd).expect("dll→pyd copy failed");
    }
    pyd
}
#[cfg(not(target_os = "windows"))]
fn ensure_pyd(p: &PathBuf) -> PathBuf {
    p.clone()
}

/* ── 3. Smoke-test 本体 ───────────────────────────────────── */
#[cfg(feature = "python")]
#[test]
fn python_bindings_smoke() {
    /* 共有ライブラリ取得 */
    let cdylib = find_cdylib();
    let module = ensure_pyd(&cdylib);
    let dir    = module.parent().expect("no parent dir");

    /* Python 起動 */
    pyo3::prepare_freethreaded_python();
    Python::with_gil(|py| -> PyResult<()> {
        /* sys.path に成果物ディレクトリを追加 */
        let sys  = py.import("sys")?;
        let path = sys.getattr("path")?.downcast_into::<PyList>()?;
        let dir_str = dir.to_str().unwrap();
        if !path.iter().any(|o| o.extract::<&str>().map_or(false, |s| s == dir_str)) {
            path.insert(0, dir_str)?;
        }

        /* モジュール import が出来るか */
        let m = py.import("poh_ack_rust")?;

        /* Ack クラスの簡易動作確認 */
        let ack_cls   = m.getattr("Ack")?;
        let dummy_sig = "1".repeat(88); // 64-byte相当
        let dummy_pk  = "1".repeat(44); // 32-byte相当
        let ack = ack_cls.call1(("tx", "2099-01-01T00:00:00Z", dummy_sig, dummy_pk))?;
        assert_eq!(ack.getattr("id")?.extract::<String>()?, "tx");

        /* check_ttl だけ確認 */
        let ok: bool = m
            .getattr("check_ttl")?
            .call1(("2099-01-01T00:00:00Z", 10_i64))?
            .extract()?;
        assert!(ok);

        Ok(())
    })
    .unwrap();
}
