//sending_DAG/rust_sending/cert_pqc/src/lib.rs
use pyo3::prelude::*;

pub mod pem;
pub mod signer;
pub mod verifier;

#[pymodule]
fn cert_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(signer::dilithium_sign_stub, m)?)?;
    m.add_function(wrap_pyfunction!(verifier::dilithium_verify_stub, m)?)?;
    Ok(())
}
