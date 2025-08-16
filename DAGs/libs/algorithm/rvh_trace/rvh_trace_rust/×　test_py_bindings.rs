// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\tests\test_py_bindings.rs
//
// Rust ⇔ PyO3 結合テスト。
// Tokio ランタイムの中で Python 側の async/await を回して
// `rvh_trace_rust` の PyO3 バインディングを実際に呼び出す。

// tests/test_py_bindings.rs

//! Rust ⇔ PyO3 結合テスト。
//! Tokio ランタイムの中で Python 側の async/await を回して
//! `rvh_trace_rust` の PyO3 バインディングを実際に呼び出す。

use pyo3::prelude::*;
use std::{
    env,
    fs,
    path::{Path, PathBuf},
};

#[cfg(target_os = "windows")]
const DYLIB_EXT: &str = "dll";
#[cfg(target_os = "macos")]
const DYLIB_EXT: &str = "dylib";
#[cfg(target_os = "linux")]
const DYLIB_EXT: &str = "so";

/// target/{debug,release}/deps から cdylib を探す
fn find_cdylib() -> PathBuf {
    let base = env::var("CARGO_TARGET_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("target"));
    for profile in ["debug", "release"] {
        let dir = base.join(profile).join("deps");
        if dir.is_dir() {
            for entry in fs::read_dir(&dir).unwrap().flatten() {
                let p = entry.path();
                if p.file_stem().and_then(|s| s.to_str()) == Some("rvh_trace_rust")
                    && p.extension().and_then(|e| e.to_str()) == Some(DYLIB_EXT)
                {
                    return p;
                }
            }
        }
    }
    panic!("rvh_trace_rust cdylib not found under {:?}", base);
}

/// Windows だけ: *.dll → *.pyd にコピーして import 可能にする
#[cfg(target_os = "windows")]
fn ensure_pyd(src: &PathBuf) -> PathBuf {
    let dst = src.with_extension("pyd");
    if !dst.exists() {
        fs::copy(src, &dst).expect("copy dll→pyd failed");
    }
    dst
}
#[cfg(not(target_os = "windows"))]
fn ensure_pyd(src: &PathBuf) -> PathBuf {
    src.clone()
}

/// PYTHONPATH にディレクトリを追加
fn add_pythonpath(dir: &Path) {
    // ← 型注釈を Vec<PathBuf> に
    let mut paths: Vec<PathBuf> = env::var_os("PYTHONPATH")
        .map(|p| env::split_paths(&p).collect())
        .unwrap_or_default();
    if !paths.iter().any(|p| p == dir) {
        paths.push(dir.to_path_buf());
        env::set_var("PYTHONPATH", env::join_paths(paths).unwrap());
    }
}

#[tokio::test]
async fn test_python_module() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        // 1) cdylib/.pyd を探して PYTHONPATH に追加
        let pyd = ensure_pyd(&find_cdylib());
        // ↑ ここで pyd.parent() は &Path を返すので OK
        add_pythonpath(pyd.parent().unwrap());

        // 2) rvh_trace_rust モジュール import + init_tracing
        let m = PyModule::import(py, "rvh_trace_rust")?;
        m.call_method1("init_tracing", ("debug",))?;

        // 3) 非同期版 span() を呼んで awaitable を取得
        let awaitable = m.call_method1("span", ("rust_test", py.None()))?;

        // 4) 独自の asyncio イベントループを作ってセット
        let asyncio = py.import("asyncio")?;
        let loop_obj = asyncio.call_method0("new_event_loop")?;
        asyncio.call_method1("set_event_loop", (loop_obj.clone(),))?;
        loop_obj.call_method1("run_until_complete", (awaitable,))?;

        Ok(())
    })?;
    Ok(())
}
