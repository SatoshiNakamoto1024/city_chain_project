// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\tests\test_py_bindings.rs
//! PoH‑ACK  Python バインディング smoke‑test

use pyo3::prelude::*;
use pyo3::types::PyList;
use std::{env, fs, path::PathBuf};
use walkdir::WalkDir;

#[cfg(target_os = "windows")]
const DLL_EXT: &str = "dll";           // ← ここを dll に
#[cfg(target_os = "macos")]
const DLL_EXT: &str = "dylib";
#[cfg(target_os = "linux")]
const DLL_EXT: &str = "so";

/// ── ① Python 用 cdylib を探す ───────────────────────────────
fn find_cdylib() -> PathBuf {
    let root = env::var("CARGO_TARGET_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("target"));

    for profile in &["debug", "release"] {
        for sub in &["", "deps"] {
            let dir = root.join(profile).join(sub);
            if !dir.is_dir() {
                continue;
            }
            for e in WalkDir::new(&dir).max_depth(1).into_iter().flatten() {
                let p = e.path();
                if let Some(ext) = p.extension().and_then(|e| e.to_str()) {
                    if !CAND_EXT.contains(&ext) { continue; }
                    let stem = p.file_stem().and_then(|s| s.to_str()).unwrap_or("");
                    let name = stem.trim_start_matches("lib");
                    if name.starts_with("poh_ack_rust") {
                        return p.to_path_buf();
                    }
                }
            }
        }
    }
    panic!("poh_ack_rust の共有ライブラリが見つかりません。`cargo build --features python`（.pyd）または `--features python-embed`（.dll）でビルドしてください。");
}

/// ── ② Windows は .dll→.pyd をコピー ─────────────────────────
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

/// ── ③ Smoke‑test ───────────────────────────────────────────
#[cfg(feature = "python")]
#[test]
fn python_bindings_smoke() {
    // ビルド成果物
    let cdylib = find_cdylib();
    let module = ensure_pyd(&cdylib);
    let dir    = module.parent().expect("no parent dir");

    // Python 起動
    pyo3::prepare_freethreaded_python();
    Python::with_gil(|py| -> PyResult<()> {
        // sys.path に追加
        let sys  = py.import("sys")?;
        let path = sys.getattr("path")?.downcast_into::<PyList>()?;
        let dir_str = dir.to_str().unwrap();
        if !path.iter().any(|o| o.extract::<&str>().map_or(false, |s| s == dir_str)) {
            path.insert(0, dir_str)?;
        }

        // import 成功を確認
        let m = py.import("poh_ack_rust")?;

        // Ack クラス生成（署名検証まではしない）
        let ack_cls = m.getattr("Ack")?;
        let dummy_sig = "1".repeat(88);   // 署名長ダミー (88 chars ≒ 64 bytes)
        let dummy_pk  = "1".repeat(44);   // 公開鍵長ダミー (44 chars ≒ 32 bytes)
        let ack = ack_cls.call1(("tx", "2099-01-01T00:00:00Z", dummy_sig, dummy_pk))?;
        assert_eq!(ack.getattr("id")?.extract::<String>()?, "tx");

        // check_ttl だけ確認
        let ok: bool = m.getattr("check_ttl")?
            .call1(("2099-01-01T00:00:00Z", 10_i64))?
            .extract()?;
        assert!(ok);

        Ok(())
    })
    .unwrap();
}
