// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\sharding.rs

use pyo3::prelude::*;
use reed_solomon_erasure::galois_8::ReedSolomon;
use thiserror::Error;

/// エラー型
#[derive(Debug, Error)]
pub enum ECError {
    #[error("ReedSolomon error: {0}")]
    RS(String),
}

/// データ → データシャード＋パリティシャード生成
pub fn encode_rs(
    data: &[u8],
    data_shards: usize,
    parity_shards: usize,
) -> Result<Vec<Vec<u8>>, ECError> {
    let rs = ReedSolomon::new(data_shards, parity_shards)
        .map_err(|e| ECError::RS(e.to_string()))?;
    let total = data_shards + parity_shards;
    let shard_size = (data.len() + data_shards - 1) / data_shards;
    let mut shards = vec![vec![0u8; shard_size]; total];

    for i in 0..data_shards {
        let start = i * shard_size;
        let end = ((i + 1) * shard_size).min(data.len());
        shards[i][..end - start].copy_from_slice(&data[start..end]);
    }

    let (data_slice, parity_slice) = shards.split_at_mut(data_shards);
    let data_refs: Vec<&[u8]> = data_slice.iter().map(|v| v.as_slice()).collect();
    let mut parity_refs: Vec<&mut [u8]> =
        parity_slice.iter_mut().map(|v| v.as_mut_slice()).collect();

    rs.encode_sep(&data_refs, &mut parity_refs)
        .map_err(|e| ECError::RS(e.to_string()))?;

    Ok(shards)
}

/// k-of-n で分割したシャードを再構築し、元データを返す。
pub fn decode_rs(
    shards: Vec<Option<Vec<u8>>>,
    data_shards: usize,
    parity_shards: usize,
) -> Result<Vec<u8>, ECError> {
    // 1) Vec<Option<Box<[u8]>>> に変換して所有権を確保
    let mut owned: Vec<Option<Box<[u8]>>> = shards
        .into_iter()
        .map(|opt| opt.map(|v| v.into_boxed_slice()))
        .collect();

    // 2) Vec<Option<&mut [u8]>> を作成する
    let mut refs: Vec<Option<&mut [u8]>> = owned
        .iter_mut()
        .map(|opt_box| {
            // Option<Box<[u8]>> を Option<&mut [u8]> に借用変換
            opt_box.as_mut().map(|boxed| boxed.as_mut())
        })
        .collect();

    // 3) ReedSolomon で復元
    let rs = ReedSolomon::new(data_shards, parity_shards)
        .map_err(|e| ECError::RS(e.to_string()))?;
    // ここで &[Option<&mut [u8]>] を渡す
    rs.reconstruct(&mut refs[..])
        .map_err(|e| ECError::RS(e.to_string()))?;

    // 4) 最初の data_shards 個を連結して返す
    let shard_len = refs[0].as_ref().unwrap().len();
    let mut out = Vec::with_capacity(data_shards * shard_len);
    for opt_slice in refs.iter().take(data_shards) {
        let slice = opt_slice
            .as_ref()
            .ok_or_else(|| ECError::RS("Missing shard".into()))?;
        out.extend_from_slice(slice);
    }
    Ok(out)
}

/// PyO3 バインディング：encode_rs のラッパー
#[pyfunction]
pub fn encode_rs_py(
    data: &[u8],
    data_shards: usize,
    parity_shards: usize,
) -> PyResult<Vec<Vec<u8>>> {
    encode_rs(data, data_shards, parity_shards)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

/// PyO3 バインディング：decode_rs のラッパー
#[pyfunction]
pub fn decode_rs_py(
    shards: Vec<Option<Vec<u8>>>,
    data_shards: usize,
    parity_shards: usize,
) -> PyResult<Vec<u8>> {
    decode_rs(shards, data_shards, parity_shards)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}
