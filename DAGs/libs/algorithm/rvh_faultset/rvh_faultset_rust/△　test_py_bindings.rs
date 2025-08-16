// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\tests\test_py_bindings.rs

use pyo3::prelude::*;
use pyo3::types::PyList;
use std::{env, fs, path::PathBuf};
use walkdir::WalkDir;

#[cfg(target_os = "windows")]
const DYLIB_EXT: &str = "dll";
#[cfg(target_os = "macos")]
const DYLIB_EXT: &str = "dylib";
#[cfg(target_os = "linux")]
const DYLIB_EXT: &str = "so";

// cargo が出力する cdylib の位置を探す
fn target_root() -> PathBuf {
    env::var("CARGO_TARGET_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("target"))
}

fn find_cdylib() -> PathBuf {
    for profile in &["debug", "release"] {
        let dir = target_root().join(profile).join("deps");
        if dir.is_dir() {
            for entry in WalkDir::new(&dir).max_depth(1).into_iter().flatten() {
                let p = entry.path();
                if let (Some(stem), Some(ext)) = (p.file_stem(), p.extension()) {
                    if stem == "rvh_faultset_rust" && ext == DYLIB_EXT {
                        return p.to_path_buf();
                    }
                }
            }
        }
    }
    panic!("failed to find rvh_faultset_rust cdylib");
}

#[cfg(target_os = "windows")]
fn ensure_pyd(path: &PathBuf) -> PathBuf {
    let pyd = path.with_extension("pyd");
    if !pyd.exists() {
        fs::copy(path, &pyd).unwrap();
    }
    pyd
}

#[cfg(not(target_os = "windows"))]
fn ensure_pyd(path: &PathBuf) -> PathBuf {
    path.to_path_buf()
}

// PYTHONPATH に cdylib のあるディレクトリを追加
fn add_pythonpath(dir: &std::path::Path) {
    let mut paths = env::split_paths(&env::var_os("PYTHONPATH").unwrap_or_default())
        .collect::<Vec<_>>();
    if !paths.iter().any(|p| p == dir) {
        paths.push(dir.to_path_buf());
        env::set_var("PYTHONPATH", env::join_paths(paths).unwrap());
    }
}

#[test]
fn python_module_roundtrip() {
    Python::with_gil(|py| -> PyResult<()> {
        // 1) cdylib/.pyd を探して PYTHONPATH 登録
        let cd = find_cdylib();
        let pyd = ensure_pyd(&cd);
        add_pythonpath(pyd.parent().unwrap());

        // 2) モジュール import
        let m = py.import("rvh_faultset_rust").expect("import failed");

        // 3) 同期版を呼ぶ
        let nodes = vec!["a", "b", "c"];
        let lats  = vec![10.0_f64, 200.0, 5.0];
        let thr   = 100.0_f64;

        // PyList::new が返す Bound<PyList> をそのまま渡す
        let py_nodes = PyList::new(py, &nodes).unwrap();
        let py_lats  = PyList::new(py, &lats).unwrap();

        // OK: f64 を直接渡す
        // ここでは f64 をそのまま渡すだけで pyo3 が PyFloat にしてくれる
        let sel: Vec<String> = m
            .getattr("failover")?
            .call1((py_nodes.clone(), py_lats.clone(), thr))?
            .extract()?;
        assert_eq!(sel, vec!["c".to_string(), "a".to_string()]);

        // 4) 非同期版を呼ぶ前に、必ず asyncio のループを作って登録しておく
        let asyncio = py.import("asyncio")?;
        let loop_obj = asyncio.call_method0("new_event_loop")?;
        asyncio.call_method1("set_event_loop", (loop_obj.clone(),))?;

        // さあこれで future_into_py 内の get_event_loop() が通る
        let fut = m
            .getattr("failover_async")?
            .call1((py_nodes, py_lats, thr))?;

        let res: Vec<String> = loop_obj
            .call_method1("run_until_complete", (fut,))?
            .extract()?;
        assert_eq!(res, vec!["c".to_string(), "a".to_string()]);

        Ok(())
    })
    .unwrap();
}
