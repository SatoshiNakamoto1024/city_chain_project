// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\sharding.rs
//! High‐level sharding & restoration wrappers.
//!
//! These functions provide a safe, metrics‐instrumented API for
//! splitting a byte‐slice into `k + m` shards and reassembling it
//! even if up to `m` shards are missing.  Includes Python bindings.

use std::time::Instant;

use pyo3::prelude::*;
use crate::core::erasure_coder::ECError;
use crate::metrics;
use reed_solomon_erasure::galois_8::ReedSolomon;

/// Split `data` into `data_shards + parity_shards` pieces.
///
/// # Errors
///
/// Returns `ECError::Algo` if the underlying Reed–Solomon constructor
/// or encode operation fails.
///
/// # Examples
///
/// ```rust
/// let shards = encode_rs(b"hello", 2, 1).unwrap();
/// assert_eq!(shards.len(), 3);
/// ```

/// High‐level wrapper: data→shards
pub fn encode_shards(
    data: &[u8],
    data_shards: usize,
    parity_shards: usize,
) -> Result<Vec<Vec<u8>>, ECError> {
    encode_rs(data, data_shards, parity_shards)
}

/// High‐level wrapper: shards→data
pub fn decode_shards(
    shards: Vec<Option<Vec<u8>>>,
    data_shards: usize,
    parity_shards: usize,
) -> Result<Vec<u8>, ECError> {
    decode_rs(shards, data_shards, parity_shards)
}

pub fn encode_rs(
    data: &[u8],
    data_shards: usize,
    parity_shards: usize,
) -> Result<Vec<Vec<u8>>, ECError> {
    let start = Instant::now();
    let rs = ReedSolomon::new(data_shards, parity_shards)
        .map_err(|e| ECError::Algo(e.to_string()))?;
    let total = data_shards + parity_shards;

    // calculate shard size (round up)
    let shard_size = (data.len() + data_shards - 1) / data_shards;
    let mut shards = vec![vec![0u8; shard_size]; total];

    // fill data shards
    for i in 0..data_shards {
        let start_idx = i * shard_size;
        let end_idx = ((i + 1) * shard_size).min(data.len());
        shards[i][..end_idx - start_idx].copy_from_slice(&data[start_idx..end_idx]);
    }

    // prepare references for in-place encode
    let (data_slice, parity_slice) = shards.split_at_mut(data_shards);
    let data_refs: Vec<&[u8]> = data_slice.iter().map(|v| v.as_slice()).collect();
    let mut parity_refs: Vec<&mut [u8]> =
        parity_slice.iter_mut().map(|v| v.as_mut_slice()).collect();

    rs.encode_sep(&data_refs, &mut parity_refs)
        .map_err(|e| ECError::Algo(e.to_string()))?;

    metrics::record("encode", start.elapsed());
    Ok(shards)
}

/// Reconstruct the original data from up to `data_shards` present shards.
///
/// `shards` should be a `Vec<Option<Vec<u8>>>` of length `data_shards + parity_shards`,
/// where `None` entries represent missing shards.
///
/// # Errors
///
/// * `ECError::Algo` if RS constructor or reconstruction fails
/// * `ECError::Algo("Missing shard")` if a needed data‐shard is still missing
///
/// # Examples
///
/// ```rust
/// let mut shards = encode_rs(b"world", 2, 1).unwrap();
/// let mut opt: Vec<_> = shards.into_iter().map(Some).collect();
/// opt[0] = None; // simulate loss
/// let recovered = decode_rs(opt, 2, 1).unwrap();
/// assert_eq!(&recovered[..5], b"world");
/// ```
pub fn decode_rs(
    shards: Vec<Option<Vec<u8>>>,
    data_shards: usize,
    parity_shards: usize,
) -> Result<Vec<u8>, ECError> {
    let start = Instant::now();

    // 1) convert to Vec<Option<Box<[u8]>>> to own the buffers
    let mut owned: Vec<Option<Box<[u8]>>> = shards
        .into_iter()
        .map(|opt| opt.map(|v| v.into_boxed_slice()))
        .collect();

    // 2) build Vec<Option<&mut [u8]>> slices for RS
    let mut refs: Vec<Option<&mut [u8]>> = owned
        .iter_mut()
        .map(|opt_box| opt_box.as_mut().map(|b| b.as_mut()))
        .collect();

    // 3) run restoration
    let rs = ReedSolomon::new(data_shards, parity_shards)
        .map_err(|e| ECError::Algo(e.to_string()))?;
    rs.reconstruct(&mut refs[..])
        .map_err(|e| ECError::Algo(e.to_string()))?;

    // 4) concatenate the first `data_shards` slices
    let mut out = Vec::with_capacity(data_shards * refs[0].as_ref().unwrap().len());
    for slot in refs.into_iter().take(data_shards) {
        let slice = slot.ok_or_else(|| ECError::Algo("Missing shard".into()))?;
        out.extend_from_slice(slice);
    }

    metrics::record("decode", start.elapsed());
    Ok(out)
}

// === Python bindings ===

/// Python‐callable wrapper for `encode_rs`.
#[pyfunction]
pub fn encode_rs_py(
    data: &[u8],
    data_shards: usize,
    parity_shards: usize,
) -> PyResult<Vec<Vec<u8>>> {
    encode_rs(data, data_shards, parity_shards)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

/// Python‐callable wrapper for `decode_rs`.
#[pyfunction]
pub fn decode_rs_py(
    shards: Vec<Option<Vec<u8>>>,
    data_shards: usize,
    parity_shards: usize,
) -> PyResult<Vec<u8>> {
    decode_rs(shards, data_shards, parity_shards)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}
