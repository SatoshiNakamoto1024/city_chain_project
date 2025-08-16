// \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\tests\test_embed.rs
// tests/test_embed.rs
#![cfg(feature = "py-embed")]

use pyo3::prelude::*;
use pyo3::types::PyList;
use pyo3::Bound;
use std::{env, path::Path};

#[test]
fn embed_python_works() {
    // ★ あなたの実インストールに合わせる
    let base = r"D:\Python\Python312";
    let dlls = format!(r"{}\DLLs", base);

    // 予防: 本当に存在するか先にチェック
    assert!(Path::new(base).exists(), "Python base not found: {}", base);
    assert!(Path::new(&dlls).exists(), "DLLs dir not found: {}", dlls);
    assert!(
        Path::new(&format!(r"{}\_socket.pyd", dlls)).exists(),
        "missing: {}\\_socket.pyd",
        dlls
    );

    // venv の影響を消して、PYTHONHOME と PATH を先に用意
    env::remove_var("VIRTUAL_ENV");
    env::remove_var("PYTHONPATH");
    env::set_var("PYTHONHOME", base);
    {
        use std::ffi::OsString;
        let mut new_path = OsString::from(format!("{};{};", base, dlls));
        if let Some(old) = env::var_os("PATH") {
            new_path.push(old);
        }
        env::set_var("PATH", new_path);
    }

    // 埋め込み初期化（GIL 外）
    pyo3::prepare_freethreaded_python();

    // GIL 内で DLL 探索ディレクトリと sys.path を調整
    Python::with_gil(|py| -> PyResult<()> {
        // ① DLL ローダに base と DLLs を追加（これが超重要）
        let os = py.import("os")?;
        os.call_method1("add_dll_directory", (base,))?;
        os.call_method1("add_dll_directory", (dlls.as_str(),))?;

        // ② sys.path にも一応入れておく（冪等）
        let sys = py.import("sys")?;
        let path: Bound<PyList> = sys.getattr("path")?.downcast_into()?;
        if !path.iter().any(|p| p.extract::<&str>().unwrap_or("") == base) {
            path.insert(0, base)?;
        }
        if !path.iter().any(|p| p.extract::<&str>().unwrap_or("") == dlls) {
            path.insert(0, dlls.as_str())?;
        }

        // ③ 実際に _socket / asyncio が読めるか
        py.import("_socket")?;
        py.import("socket")?;
        py.import("asyncio")?;
        Ok(())
    }).unwrap();
}
