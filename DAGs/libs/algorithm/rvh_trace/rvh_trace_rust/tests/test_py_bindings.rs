// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\tests\test_py_bindings.rs

// tests/test_py_bindings.rs

//! Rust ⇔ PyO3 経由で Python 関数を呼び出す結合テスト。
//! Tokio のテストマクロで非同期に動かしつつ、
//! Python 側の asyncio で awaitable を実行します。
use std::ffi::CString; 
use pyo3::types::PyList;        // 追加
use pyo3::types::PyDict;
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

/// target/{debug,release}/deps から `rvh_trace_rust.{ext}` を探す
fn find_cdylib() -> PathBuf {
    let target_dir = env::var("CARGO_TARGET_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("target"));

    for profile in &["debug", "release"] {
        let deps = target_dir.join(profile).join("deps");
        if deps.is_dir() {
            for entry in fs::read_dir(&deps).unwrap().flatten() {
                let p = entry.path();
                if p.extension().and_then(|e| e.to_str()) == Some(DYLIB_EXT) {
                    //   Windows : rvh_trace_rust.dll
                    //   macOS   : librvh_trace_rust-<hash>.dylib
                    //   Linux   : librvh_trace_rust-<hash>.so
                    let stem = p.file_stem().and_then(|s| s.to_str()).unwrap_or("");
                    if stem.ends_with("rvh_trace_rust") || stem.contains("rvh_trace_rust-") {
                        return p;
                    }
                }
            }
        }
    }
    panic!("rvh_trace_rust cdylib not found under {:?}", target_dir);
}

/// Windows 上では *.dll → *.pyd にコピーして Python で import 可能にする
#[cfg(target_os = "windows")]
fn ensure_pyd(src: &Path) -> PathBuf {
    let dst = src.with_extension("pyd");
    if !dst.exists() {
        fs::copy(src, &dst).expect("copy dll→pyd failed");
    }
    dst
}

/// Unix/macOS はそのまま返す
#[cfg(not(target_os = "windows"))]
fn ensure_pyd(src: &Path) -> PathBuf {
    // 例: librvh_trace_rust‑abcd.so  →  rvh_trace_rust.so
    let dst = src.with_file_name("rvh_trace_rust.so");
    if !dst.exists() {
        // ハードリンクでも OK。書き込み権限が無ければ std::os::unix::fs::symlink を使う
        std::fs::copy(src, &dst).expect("lib→so copy failed");
    }
    dst
}

/// PYTHONPATH にディレクトリを追加するユーティリティ
fn add_pythonpath(dir: &Path) {
    let mut paths: Vec<PathBuf> = env::var_os("PYTHONPATH")
        .map(|os| env::split_paths(&os).collect())
        .unwrap_or_default();
    if !paths.iter().any(|p| p == dir) {
        paths.push(dir.to_path_buf());
        env::set_var("PYTHONPATH", env::join_paths(&paths).unwrap());
    }
}

/// Tokio のテストマクロで非同期関数を実行
#[tokio::test]
async fn test_python_module() -> PyResult<()> {
    // ── 0. Windows の場合、Python のバイナリと DLLs、Lib を PATH に追加 ───────────
    let python_home = env::var("PYTHON_HOME")
        .unwrap_or_else(|_| "D:\\Python\\Python312".to_string());
    let dlls_dir = PathBuf::from(&python_home).join("DLLs");
    let lib_dir  = PathBuf::from(&python_home).join("Lib");
    let orig_path = env::var("PATH").unwrap_or_default();
    let new_path = format!(
        "{};{};{};{}",
        dlls_dir.display(),
        python_home,
        lib_dir.display(),
        orig_path
    );
    env::set_var("PATH", &new_path);

    // ── 1. Python 側 API 呼び出し ────────────────────────────────────
    Python::with_gil(|py| -> PyResult<()> {
        // 1.1) sys.path に Lib / DLLs / python_home を追加
        // PyO3 0.25 以降: &CStr が必要
        use std::ffi::CString;          // ← 追加しても良い
        let code = CString::new(format!(
            "import sys; \
             sys.path.insert(0, r\"{}\"); \
             sys.path.insert(0, r\"{}\"); \
             sys.path.insert(0, r\"{}\")",
            lib_dir.display(),
            dlls_dir.display(),
            python_home
        )).expect("CString::new");

        py.run(code.as_c_str(), None, None)?;

        // 1.2) Python の asyncio モジュール取得
        let asyncio = py.import("asyncio")?;     // ← ここだけ &str で良い
        // ループを用意して「現在のループ」に登録
        let loop_obj = asyncio.call_method0("new_event_loop")?;
        asyncio.call_method1("set_event_loop", (loop_obj.clone(),))?;

        // 1.3) ビルド済み cdylib/.pyd を見つけて PYTHONPATH に追加
        let cdylib = find_cdylib();
        let pyd = ensure_pyd(&cdylib);
        add_pythonpath(pyd.parent().unwrap());
        
        // このように `with_gil` の中に移動して表示させる
        // いま動いている Python にも同じディレクトリを挿入する
        {
            let sys     = py.import("sys")?;
            use pyo3::types::PyList;
            let sys_path = sys
                .getattr("path")?
                .downcast_into::<PyList>()?;   // ← ここがポイント

            let dir_str = pyd
                .parent()
                .unwrap()
                .to_str()
                .expect("utf‑8");

            if !sys_path.iter().any(|o| o.extract::<&str>().map_or(false, |s| s == dir_str)) {
                sys_path.insert(0, dir_str)?;
            }
        }

        println!(
            " PYTHONPATH に追加済み: {}",
            pyd.parent().unwrap().display()
        );

        // 1.4) rvh_trace_rust モジュールのインポートと init_tracing 呼び出し
        let m = PyModule::import(py, "rvh_trace_rust")?;   // ← 同上
        m.getattr("init_tracing")?.call1(("debug",))?;

        // ① locals（辞書）を先に用意
        let locals = PyDict::new(py);
        locals.set_item("trace", &m)?;

        // ② coroutine を定義（左端にそろえる）
        let code = CString::new(
            //      ↓ 行頭に一切インデントを入れない！
            "async def _main():\n    await trace.span('rust_test')\n"
        ).unwrap();
        py.run(code.as_c_str(), Some(&locals), Some(&locals))?;

        // ③ _main() を eval して Future を得る
        let fut = py.eval(
            CString::new("_main()").unwrap().as_c_str(),
            Some(&locals),          // ← ここを None → Some(&locals)
            Some(&locals),
        )?;

        // ④ ループで実行
        loop_obj.call_method1("run_until_complete", (fut,))?;

        // （最後に）
        Ok(())
    })?;

    // テスト成功
    Ok(())
}
