use pyo3::prelude::*;

pub mod types;
pub mod recovery;

#[pymodule]
fn receiving_DAG(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(recovery::register_repair_ack, m)?)?;
    m.add_function(wrap_pyfunction!(recovery::collect_valid_ack, m)?)?;
    Ok(())
}
