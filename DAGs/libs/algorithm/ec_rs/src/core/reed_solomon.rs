// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\reed_solomon.rs
//! Reed–Solomon 符号による Erasure Coding 実装
//!
//! - リソース：reed-solomon-erasure v5.0
//! - SIMD 有効化済み (feature = "simd")
//! - `ECConfig` で指定されたパラメータに従い、k-of-n で分割・復元を行う

use crate::ECConfig;
use crate::core::{ErasureCoder, ECError};
use reed_solomon_erasure::galois_8::ReedSolomon;
use reed_solomon_erasure::Error as RSError;
use std::cmp;

/// Reed–Solomon コーディング器
pub struct ReedSolomonCoder {
    data_shards: usize,
    parity_shards: usize,
    min_shard_size: usize,
}

impl ReedSolomonCoder {
    /// 新しいインスタンスを生成します。
    ///
    /// # 引数
    /// - `cfg`: ECConfig から読み込んだ構成情報
    ///
    /// # エラー
    /// - `cfg.data_shards == 0` または `cfg.parity_shards == 0` の場合は `ECError::Algo`
    pub fn new(cfg: &ECConfig) -> Result<Self, ECError> {
        if cfg.data_shards == 0 || cfg.parity_shards == 0 {
            return Err(ECError::Algo(
                "data_shards と parity_shards は 1 以上でなければなりません".into(),
            ));
        }
        Ok(Self {
            data_shards: cfg.data_shards,
            parity_shards: cfg.parity_shards,
            min_shard_size: cfg.min_shard_size,
        })
    }

    /// 入力データ長と設定から実際に使うシャード長を計算します。
    fn shard_size_for(&self, data_len: usize) -> usize {
        let base = (data_len + self.data_shards - 1) / self.data_shards;
        cmp::max(base, self.min_shard_size)
    }
}

impl ErasureCoder for ReedSolomonCoder {
    /// データを `data_shards + parity_shards` 個のシャードに分割して返します。
    ///
    /// # 戻り値
    /// - `Ok(shards)` の場合、`shards.len() == data_shards + parity_shards`、
    ///   各要素は長さ `shard_size` の `Vec<u8>` です。
    /// - 途中で失敗すると `ECError::Algo` か `ECError::Io` を返します。
    fn encode(&self, data: &[u8], _cfg: &ECConfig) -> Result<Vec<Vec<u8>>, ECError> {
        // ReedSolomon 構築
        let rs = ReedSolomon::new(self.data_shards, self.parity_shards)
            .map_err(|e| ECError::Algo(format!("ReedSolomon::new に失敗: {}", e)))?;

        let total_shards = self.data_shards + self.parity_shards;
        let shard_size = self.shard_size_for(data.len());
        let mut shards = vec![vec![0u8; shard_size]; total_shards];

        // データ部分を埋める
        for (i, chunk) in data.chunks(shard_size).enumerate() {
            shards[i][..chunk.len()].copy_from_slice(chunk);
        }

        // 参照スライスを準備
        let data_refs: Vec<&[u8]> = shards[..self.data_shards]
            .iter()
            .map(|s| &s[..])
            .collect();
        let mut parity_refs: Vec<&mut [u8]> = shards[self.data_shards..]
            .iter_mut()
            .map(|s| &mut s[..])
            .collect();

        // in-place エンコード
        rs.encode_sep(&data_refs, &mut parity_refs)
            .map_err(|e| ECError::Algo(format!("encode_sep エラー: {}", e)))?;

        Ok(shards)
    }

    /// `Vec<Option<Vec<u8>>>`（`None` は欠損シャード）を復元し、元データを返します。
    ///
    /// # 戻り値
    /// - `Ok(data)` の場合、復元されたバイト列
    /// - 途中で失敗すると `ECError::Algo` か `ECError::Io` を返します。
    fn decode(
        &self,
        shards: Vec<Option<Vec<u8>>>,
        _cfg: &ECConfig,
    ) -> Result<Vec<u8>, ECError> {
        // ReedSolomon 構築
        let rs = ReedSolomon::new(self.data_shards, self.parity_shards)
            .map_err(|e| ECError::Algo(format!("ReedSolomon::new に失敗: {}", e)))?;

        // Vec<Option<Box<[u8]>>> に変換して所有権を確保
        // 1) 元シャードを Box<[u8]> で所有し
        let mut owned: Vec<Option<Box<[u8]>>> = shards
            .into_iter()
            .map(|opt| opt.map(|v| v.into_boxed_slice()))
            .collect();

        // 2) Option<&mut [u8]> を生成して渡す
        let mut refs: Vec<Option<&mut [u8]>> = owned
            .iter_mut()
            .map(|opt_box| opt_box.as_mut().map(|b| b.as_mut()))
            .collect();

        // 3) ここで正しく reconstruct
        let rs = ReedSolomon::new(k, m)?;
        rs.reconstruct(&mut refs[..])?;

        // 最初の data_shards 個を連結して返す
        let mut out = Vec::with_capacity(self.data_shards * self.min_shard_size);
        for i in 0..self.data_shards {
            let slice = refs[i]
                .as_ref()
                .ok_or_else(|| ECError::Algo("復元後にシャードが None です".into()))?;
            out.extend_from_slice(slice);
        }

        Ok(out)
    }
}
