// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\src\bindings.rs

use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

use crate::faultset::failover;
use crate::error::FaultsetError;

/// Python wrapper for the Rust `failover` function.
///
/// Args:
///     nodes: List of node IDs (strings).
///     latencies: Corresponding list of latencies (floats).
///     threshold: Maximum acceptable latency.
///
/// Returns:
///     List of surviving node IDs (strings) after failover.
///
/// Raises:
///     ValueError: if inputs are invalid or no nodes survive.
#[pyfunction]
#[pyo3(text_signature = "(nodes, latencies, threshold, /)")]
fn failover_py(
    nodes: Vec<String>,
    latencies: Vec<f64>,
    threshold: f64,
) -> PyResult<Vec<String>> {
    failover(&nodes, &latencies, threshold).map_err(|e| {
        // Map all Rust-side errors into Python ValueError
        pyo3::exceptions::PyValueError::new_err(e.to_string())
    })
}

/// Python module initialization.
///
/// The module name **must** match the crate name (`rvh_faultset_rust`) so that
/// Python’s `import rvh_faultset_rust` finds the `PyInit_rvh_faultset_rust` symbol.
#[pymodule]
fn rvh_faultset_rust(py: Python<'_>, m: &PyModule) -> PyResult<()> {
    // Register the `failover` function under its Python wrapper name.
    m.add_function(wrap_pyfunction!(failover_py, m)?)?;
    // Expose the crate version from Cargo.toml
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
