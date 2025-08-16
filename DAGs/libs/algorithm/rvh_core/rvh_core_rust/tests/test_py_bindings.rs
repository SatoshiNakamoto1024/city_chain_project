// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\tests\test_py_bindings.rs
//! tests/test_py_bindings.rs
//! ----------------------------------------------------------
//! * Rust cdylib (rvh_core_rust.{dll|so|dylib}) を動的に探し、
//!   Python から `rendezvous_hash()` を呼び出せることを確認する結合テスト。
//! * Windows では DLL→PYD へコピーして import 可能にする。
//! ----------------------------------------------------------

use pyo3::prelude::*;
use pyo3::types::PyList;
use std::{
    env,
    fs,
    path::{Path, PathBuf},
};
use walkdir::WalkDir;

#[cfg(target_os = "windows")]
const DYLIB_EXT: &str = "dll";
#[cfg(target_os = "linux")]
const DYLIB_EXT: &str = "so";
#[cfg(target_os = "macos")]
const DYLIB_EXT: &str = "dylib";

/// target/{debug,release}/ 以下から rvh_core_rust.* を探す
fn find_cdylib() -> PathBuf {
    let tgt_root = env::var("CARGO_TARGET_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("target"));

    ["debug", "release"]
        .into_iter()
        .flat_map(|p| WalkDir::new(tgt_root.join(p)))
        .filter_map(Result::ok)
        .map(|e| e.into_path())
        .find(|p| {
            p.file_stem()
                .is_some_and(|s| s.to_string_lossy().starts_with("rvh_core_rust"))
                && p.extension().and_then(|e| e.to_str()) == Some(DYLIB_EXT)
        })
        .expect("build first!")
}

/// Windows は *.dll→*.pyd を用意
#[cfg(target_os = "windows")]
fn ensure_pyd(dll: &Path) -> PathBuf {
    let pyd = dll.with_extension("pyd");
    if !pyd.exists() {
        fs::copy(dll, &pyd).expect("copy dll→pyd failed");
    }
    pyd
}
#[cfg(not(target_os = "windows"))]
fn ensure_pyd(p: &Path) -> PathBuf {
    p.to_path_buf()
}

/// PYTHONPATH へディレクトリを追加
fn add_pythonpath(dir: &Path) {
    let mut paths: Vec<PathBuf> =
        env::split_paths(&env::var_os("PYTHONPATH").unwrap_or_default()).collect();
    if !paths.iter().any(|p| p == dir) {
        paths.push(dir.to_path_buf());
        env::set_var("PYTHONPATH", env::join_paths(paths).unwrap());
    }
}

#[test]
fn python_roundtrip() {
    // ── 1. cdylib → pyd を準備して PYTHONPATH を通す ──────────────
    let cdylib = ensure_pyd(&find_cdylib());
    add_pythonpath(cdylib.parent().unwrap());

    // ── 2. Python 側から呼び出して検証 ────────────────────────────
    Python::with_gil(|py| -> PyResult<()> {
        let rvh = py.import("rvh_core_rust")?;

        let nodes = vec!["node-a", "node-b", "node-c"];
        let nodes_py = PyList::new(py, &nodes)?;          // ← ★ ここでアンラップ

        let sel: Vec<String> = rvh
            .getattr("rendezvous_hash")?
            .call1((nodes_py, "object-42", 2usize))?      // ← Bound<PyList> を渡す
            .extract()?;

        assert_eq!(sel.len(), 2);
        for s in &sel {
            assert!(nodes.contains(&s.as_str()));
        }
        Ok(())
    })
    .unwrap();
}
