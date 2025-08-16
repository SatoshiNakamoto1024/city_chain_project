// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\design\qcpeg.rs
//! QC-PEG 行列生成
//! 1. PEG (dv, dc) で骨格グラフを作る
//! 2. circulant サイズ `z` で各エッジを循環シフト
//! 3. 最終的に H は (m × n) のブロック循環疎行列
use rand::{Rng, SeedableRng, seq::SliceRandom};

use super::validate;

#[derive(Debug, Clone, Copy)]
pub struct QcPegConfig {
    pub data_shards: usize,
    pub parity_shards: usize,
    pub circulant: usize,
    pub dv: usize,
    pub dc: usize,
}

/// CSR 風の疎行列（行ごとの (col,coef) ベクタ保持）
pub type SparseRow = Vec<(usize, u8)>;
pub type SparseMatrix = Vec<SparseRow>;

/// 生成メイン
pub fn generate(cfg: &QcPegConfig, seed: u64) -> SparseMatrix {
    let n = cfg.data_shards + cfg.parity_shards;
    let m = cfg.parity_shards;
    let z = cfg.circulant;

    // 1. PEG: 隣接リスト (行→列) を埋める
    let mut rng = rand::rngs::StdRng::seed_from_u64(seed);
    let mut rows: SparseMatrix = vec![Vec::with_capacity(cfg.dc); m];

    // 簡易 PEG: 行ごとに dv 個・列ごとに dc 個をなるべく一様割付
    let mut col_deg = vec![0usize; n];
    for r in 0..m {
        while rows[r].len() < cfg.dc {
            // 低次数列を優先
            let col = weighted_pick(&col_deg, &mut rng);
            if rows[r].iter().any(|&(c, _)| c == col) { continue; }
            rows[r].push((col, 1));          // 係数は 1 (GF(2))
            col_deg[col] += 1;
        }
    }

    // 2. QC: 各エッジに循環シフト 0..z-1 をランダム付与
    for row in &mut rows {
        for (c, coef) in row.iter_mut() {
            *coef = (rng.gen::<u8>() % 255).max(1);      // 非ゼロ
            *c = (*c % cfg.data_shards) * z + rng.gen_range(0..z);
        }
    }

    // 3. 妥当性チェック
    assert!(validate::girth(&rows) >= 6, "girth<6 ; regenerate seed");

    rows
}

/// 低次数列ほど確率高く選ぶ単純ルーレット
fn weighted_pick(deg: &[usize], rng: &mut impl Rng) -> usize {
    let max = *deg.iter().max().unwrap_or(&1) + 1;
    let candidates: Vec<_> = deg.iter()
        .enumerate()
        .filter(|(_, &d)| rng.gen_range(0..max) >= d)
        .map(|(i, _)| i)
        .collect();
    *candidates.choose(rng).unwrap_or(&0)
}
