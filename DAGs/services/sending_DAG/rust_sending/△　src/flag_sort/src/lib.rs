// sending_DAG\rust_sending\flag_sort\src\lib.rs
use pyo3::prelude::*;

pub mod types;
pub mod sorter;

#[pymodule]
fn flag_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sorter::sort_by_flag, m)?)?;
    Ok(())
}
