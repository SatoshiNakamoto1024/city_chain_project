// D:\city_chain_project\DAGs\libs\algorithm\rvh_weighted\src\weighted.rs

use crate::utils::score128;
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// 各ノードのメタ情報
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeInfo<'a> {
    /// ノード ID
    pub id: &'a str,
    /// PoS ステーク量
    pub stake: u64,
    /// 処理キャパシティ (tx/s)
    pub capacity: u64,
    /// RTT (往復遅延) [ms]
    pub rtt_ms: f64,
}

impl<'a> NodeInfo<'a> {
    /// コンストラクタ
    pub fn new(id: &'a str, stake: u64, capacity: u64, rtt_ms: f64) -> Self {
        Self {
            id,
            stake,
            capacity,
            rtt_ms,
        }
    }
}

/// ランタイムエラー
#[derive(Debug, Error, PartialEq)]
pub enum WeightError {
    /// ノード配列が空
    #[error("node list is empty")]
    Empty,
    /// k がノード数を超過
    #[error("k = {0} exceeds n = {1}")]
    TooMany(usize, usize),
}

/// 重み付き HRW により上位 k ノードを返す
pub fn weighted_select<'a>(
    nodes: &[NodeInfo<'a>],
    key: &str,
    k: usize,
) -> Result<Vec<&'a str>, WeightError> {
    if nodes.is_empty() {
        return Err(WeightError::Empty);
    }
    if k == 0 || k > nodes.len() {
        return Err(WeightError::TooMany(k, nodes.len()));
    }

    // ① RTT 正規化: 最小/最大を f64 型で初期化
    let (min_rtt, max_rtt) = nodes.iter().fold((f64::MAX, 0.0_f64), |(mi, ma), n| {
        (mi.min(n.rtt_ms), ma.max(n.rtt_ms))
    });
    let rtt_span = (max_rtt - min_rtt).max(1e-9);

    // ② 各ノードのスコアを求める
    let mut scored: Vec<(u128, &str)> = Vec::with_capacity(nodes.len());
    for n in nodes {
        // Base スコア (エラーなら 0)
        let base: u128 = score128(n.id, key).unwrap_or(0);

        // ステーク: ln で圧縮
        let stake_w = (n.stake as f64).ln();

        // キャパシティ: sqrt で緩和
        let cap_w = (n.capacity as f64).sqrt();

        // RTT: 低いほど良い ⇒ 0～1 に正規化して反転
        let rtt_norm = 1.0 - (n.rtt_ms - min_rtt) / rtt_span;

        // 合成重み
        let weight_f64 = stake_w + cap_w + rtt_norm * 100.0;
        let weight = (weight_f64 * 1e6) as u128;

        // u128同士の乗算
        scored.push((base.wrapping_mul(weight), n.id));
    }

    // ③ スコア降順ソート＆上位 k 抽出
    scored.sort_by(|a, b| b.0.cmp(&a.0));
    Ok(scored.into_iter().take(k).map(|(_, id)| id).collect())
}
