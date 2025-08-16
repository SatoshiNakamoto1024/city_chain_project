// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\tests\test_py_bindings.rs
// tests/test_py_bindings.rs
// -----------------------------------------------------------
// * cargo test 直後でも pyo3 拡張モジュール (Windows は .dll) を
//   Python が見つけられるように .pyd へコピーして PYTHONPATH を調整
// * Linux/macOS は '.so' / '.dylib' をそのまま使う
// -----------------------------------------------------------

use pyo3::prelude::*;
use pyo3::types::{PyList, PyTuple};
use walkdir::WalkDir;
use std::{env, fs, path::{Path, PathBuf}};

#[cfg(target_os = "windows")]
const DYLIB_EXT: &str = "dll";
#[cfg(target_os = "macos")]
const DYLIB_EXT: &str = "dylib";
#[cfg(target_os = "linux")]
const DYLIB_EXT: &str = "so";

/// target/{debug|release} ルート
fn target_root() -> PathBuf {
    env::var("CARGO_TARGET_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("target"))
}

/// 拡張モジュールを探索
fn find_cdylib() -> PathBuf {
    ["debug", "release"]
        .into_iter()
        .flat_map(|p| WalkDir::new(target_root().join(p)))
        .filter_map(|e| e.ok())
        .map(|e| e.into_path())
        .find(|p| {
            p.file_stem().map(|s| s == "rvh_rust").unwrap_or(false)
                && p.extension().and_then(|s| s.to_str()) == Some(DYLIB_EXT)
        })
        .expect("rvh_rust cdylib not built; run `cargo build --lib` first")
}

/// Windows では rvh_rust.dll → rvh_rust.pyd を用意
#[cfg(target_os = "windows")]
fn ensure_pyd(dll_path: &Path) -> PathBuf {
    let pyd_path = dll_path.with_extension("pyd");
    if !pyd_path.exists() {
        fs::copy(dll_path, &pyd_path)
            .expect("copy dll→pyd failed");
    }
    pyd_path
}
#[cfg(not(target_os = "windows"))]
fn ensure_pyd(path: &Path) -> PathBuf {
    path.to_path_buf()
}

/// PYTHONPATH へディレクトリを追加
fn add_pythonpath(dir: &Path) {
    let mut paths: Vec<PathBuf> =
        env::split_paths(&env::var_os("PYTHONPATH").unwrap_or_default()).collect();
    if !paths.iter().any(|p| p == dir) {
        paths.push(dir.to_owned());
        env::set_var("PYTHONPATH", env::join_paths(paths).unwrap());
    }
}

#[test]
fn python_module_roundtrip() {
    let cdylib = ensure_pyd(&find_cdylib());
    add_pythonpath(cdylib.parent().expect("parent"));

    Python::with_gil(|py| {
        let rvh = py.import("rvh_rust")
            .expect("import rvh_rust failed - did you build the cdylib?");

        let nodes = vec!["a", "b", "c"];
        let args = PyTuple::new(
            py,
            &[
                PyList::new(py, &nodes).to_object(py),
                "hello-key".to_object(py),
                2usize.to_object(py),
            ],
        );
        let sel: Vec<String> = rvh
            .getattr("rendezvous_hash").unwrap()
            .call1(args).unwrap()
            .extract().unwrap();

        assert_eq!(sel.len(), 2);
        for s in &sel {
            assert!(nodes.contains(&s.as_str()));
        }
    });
}
