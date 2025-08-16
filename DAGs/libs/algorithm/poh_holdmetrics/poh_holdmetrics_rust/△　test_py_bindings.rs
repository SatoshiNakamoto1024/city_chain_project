// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\tests\test_py_bindings.rs
#![cfg(feature = "python")]

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::{
    env,
    fs,
    ffi::OsString,
    path::{Path, PathBuf},
    sync::Once,
};

const STEM: &str = "poh_holdmetrics_rust";

// ─────────────────── ① PATH を拡張（Python未初期化でもOKな範囲だけ） ─────
#[cfg(windows)]
fn prepend_path(dir: &str) {
    let mut new_path = OsString::from(dir);
    new_path.push(";");
    if let Some(old) = env::var_os("PATH") {
        new_path.push(old);
    }
    env::set_var("PATH", new_path);
}

static INIT_ENV: Once = Once::new();
fn ensure_host_dll_path() {
    INIT_ENV.call_once(|| {
        #[cfg(windows)]
        {
            // 未初期化で Python API を触らないよう、VENV のみを PATH へ
            if let Ok(venv) = env::var("VIRTUAL_ENV") {
                prepend_path(&venv);
                prepend_path(&format!(r"{}\DLLs", venv));
            }
        }
    });
}

// ─────────────────── ② Python を一度だけ初期化 ──────────────────────────
static INIT_PY: Once = Once::new();
fn ensure_python_ready() {
    ensure_host_dll_path();
    INIT_PY.call_once(|| {
        // 自動初期化を切っているので手動で初期化
        pyo3::prepare_freethreaded_python();
    });
}

// ─────────────────── ③ .pyd / .dll を探すヘルパ ─────────────────────────
fn find_pyd() -> Option<PathBuf> {
    let target = env::var("CARGO_TARGET_DIR").unwrap_or_else(|_| "target".into());
    let profile = env::var("PROFILE").unwrap_or_else(|_| "debug".into());
    let deps = Path::new(&target).join(&profile).join("deps");
    if let Some(p) = glob_find(&deps) {
        return Some(p);
    }
    if let Ok(venv) = env::var("VIRTUAL_ENV") {
        let site = Path::new(&venv)
            .join("Lib")
            .join("site-packages")
            .join(STEM);
        if let Some(p) = glob_find(&site) {
            return Some(p);
        }
    }
    None
}

fn glob_find(dir: &Path) -> Option<PathBuf> {
    if !dir.exists() { return None; }
    for entry in fs::read_dir(dir).ok()? {
        let p = entry.ok()?.path();
        let ext = p.extension()?.to_str()?;
        if matches!(ext, "pyd" | "dll")
            && p.file_stem()?.to_str()?.starts_with(STEM)
        {
            return Some(p);
        }
    }
    None
}

// ───── sys.path にディレクトリを追加 ───────────────────────────────────
fn add_path(py: Python<'_>, dir: &Path) -> PyResult<()> {
    let sys = py.import("sys")?;
    let path_obj = sys.getattr("path")?;
    let path = path_obj.downcast::<PyList>()?;
    let dir_str = dir.to_str().unwrap();
    if !path.iter().any(|item| item.extract::<&str>().unwrap_or("") == dir_str) {
        path.insert(0, dir_str)?;
    }
    Ok(())
}

// ───── Windows: stdlib DLL の場所を Python 側にも伝える ─────
fn add_stdlib_dirs(py: Python<'_>) -> PyResult<()> {
    #[cfg(windows)]
    {
        let os = py.import("os")?;
        // base は Python 初期化後に Python 側から取得する（←ここならOK）
        if let Some(base) = cpython_base_dir(py) {
            let base_dir = std::path::Path::new(&base);
            let dlls    = base_dir.join("DLLs");
            os.call_method1("add_dll_directory", (base.as_str(),))?;
            if dlls.exists() {
                os.call_method1("add_dll_directory", (dlls.to_str().unwrap(),))?;
            }
            add_path(py, base_dir)?;
            if dlls.exists() { add_path(py, &dlls)?; }
        }
        if let Ok(venv) = std::env::var("VIRTUAL_ENV") {
            let venv_dir = std::path::Path::new(&venv);
            let dlls     = venv_dir.join("DLLs");
            os.call_method1("add_dll_directory", (venv.as_str(),))?;
            if dlls.exists() {
                os.call_method1("add_dll_directory", (dlls.to_str().unwrap(),))?;
            }
            add_path(py, venv_dir)?;
            if dlls.exists() { add_path(py, &dlls)?; }
        }
    }
    Ok(())
}

/// CPython の installed_base を取得 (例: D:\Python\Python312) – Python初期化後にだけ呼ぶ
#[cfg(windows)]
fn cpython_base_dir(py: Python<'_>) -> Option<String> {
    let sysconfig = py.import("sysconfig").ok()?;
    sysconfig
        .getattr("get_config_var").ok()?
        .call1(("installed_base",)).ok()?
        .extract::<String>().ok()
}

/// .pyd を用意できない CI などでは skip
macro_rules! skip {
    ($py:expr, $msg:literal) => {{
        let pytest = $py.import("pytest").unwrap();
        pytest.call_method1("skip", ($msg,)).unwrap();
    }};
}

//────────────────────────────────────────────────────────
// 1. calculate_score — 保持時間ゼロならスコア 0
//────────────────────────────────────────────────────────
#[test]
fn python_calculate_score() {
    ensure_python_ready();
    Python::with_gil(|py| {
        let Some(pyd) = find_pyd() else {
            skip!(py, ".pyd not found; skipping");
            return;
        };
        add_path(py, pyd.parent().unwrap()).unwrap();
        add_stdlib_dirs(py).unwrap();

        let m = py.import(STEM).unwrap();
        let calc = m.getattr("calculate_score").unwrap();
        let ev_cls = m.getattr("PyHoldEvent").unwrap();

        let ev = ev_cls
            .call1(("tk", "hd", 1_000_i64, 1_000_i64, 1.0_f64))
            .unwrap();
        let score: f64 = calc.call1(([ev],)).unwrap().extract().unwrap();
        assert_eq!(score, 0.0);
    });
}

//────────────────────────────────────────────────────────
// 2. PyAggregator end-to-end（同期メソッドでクラッシュ回避）
//────────────────────────────────────────────────────────
#[test]
fn python_aggregator_flow() {
    ensure_python_ready(); // ← 一度だけ pyo3::prepare_freethreaded_python()

    Python::with_gil(|py| {
        let Some(pyd) = find_pyd() else { skip!(py, ".pyd not found"); return; };
        add_path(py, pyd.parent().unwrap()).unwrap();
        add_stdlib_dirs(py).unwrap();

        let m      = py.import(STEM).unwrap();
        let agg    = m.getattr("PyAggregator").unwrap().call0().unwrap();
        let ev_cls = m.getattr("PyHoldEvent").unwrap();
        let ev     = ev_cls
            .call1(("tk","hd",1_000_i64,1_000_i64,1.0_f64))
            .unwrap();

        // 非同期は使わない（短命プロセスでの finalize 競合を避ける）
        agg.call_method1("record_sync", (ev,)).unwrap();

        let snapshot: Vec<(String, f64)> =
            agg.call_method0("snapshot").unwrap().extract().unwrap();
        assert_eq!(snapshot.as_slice(), &[("hd".to_string(), 0.0)]);
    });
}
