// D:\city_chain_project\Algorithm\PoP\pop_rust_src\src\lib.rs
//! pop_rust ライブラリ
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

pub mod events;
pub mod polygons;
pub mod types;

/// Python 拡張モジュールの登録
#[pymodule]
fn pop_rust(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    use pyo3::wrap_pyfunction;
    m.add_function(wrap_pyfunction!(polygons::load_polygons_from_dir, m)?)?;
    m.add_function(wrap_pyfunction!(polygons::query_point, m)?)?;
    m.add_function(wrap_pyfunction!(events::check_city_event, m)?)?;
    m.add_function(wrap_pyfunction!(events::check_location_event, m)?)?;
    Ok(())
}
