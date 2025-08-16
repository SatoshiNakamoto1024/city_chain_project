// D:\city_chain_project\Algorithm\PoP\pop_rust\src\lib.rs
use pyo3::prelude::*;

pub mod types;
pub mod polygons;
pub mod events;

#[pymodule]
fn pop_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(polygons::load_polygons, m)?)?;
    m.add_function(wrap_pyfunction!(polygons::query_point,  m)?)?;
    Ok(())
}
