//sending_DAG/rust_sending/dag_core/src/dpos_parallel.rs
// dpos_parallel.rs でオンライン/オフライン + 詳細理由を計算し、DposResult を返す

/*!
dpos_parallel.rs

拡張版 DPoS 並列承認ロジック:
- 各バリデータが (online: bool, stake: f64, vote: bool) を持つ
- オフラインは無視
- approve率 = stake(approve)/総stake
- 閾値 (threshold_ratio) を超えれば承認 success
- reason に詳細文字列を入れて Python 側が参照できる
*/

use serde::{Serialize, Deserialize};
use rayon::prelude::*;

/// バリデータ情報
#[derive(Serialize, Deserialize, Debug)]
pub struct DposValidator {
    pub validator_id: String,
    pub stake: f64,
    pub online: bool,
    pub vote: bool, // approve or reject
}

/// バッチごとの投票データ
#[derive(Serialize, Deserialize, Debug)]
pub struct DposBatchVotes {
    pub batch_hash: String,
    pub validators: Vec<DposValidator>,
}

/// 集計結果
#[derive(Serialize, Deserialize, Debug)]
pub struct DposResult {
    pub batch_hash: String,
    pub approved: bool,
    pub total_stake: f64,
    pub stake_approved: f64,
    pub approve_rate: f64, // stake_approved / total_stake
    pub threshold: f64,
    pub reason: String,
}

/// 並列集計
///  - vote_lists: 複数バッチの投票
///  - threshold_ratio: e.g. 0.66
/// 返却: バッチごとの DposResult の配列
pub fn parallel_dpos_collect(vote_lists: Vec<DposBatchVotes>, threshold_ratio: f64) -> Vec<DposResult> {
    vote_lists.into_par_iter()
        .map(|bv| {
            // オンラインのみ
            let online_vals: Vec<&DposValidator> = bv.validators.iter().filter(|v| v.online).collect();
            let total_stake: f64 = online_vals.iter().map(|v| v.stake).sum();

            if total_stake <= 0.0 {
                // no online stake => fail
                return DposResult {
                    batch_hash: bv.batch_hash,
                    approved: false,
                    total_stake: 0.0,
                    stake_approved: 0.0,
                    approve_rate: 0.0,
                    threshold: threshold_ratio,
                    reason: "No online validators or zero total stake".into(),
                };
            }
            let stake_approved: f64 = online_vals.iter().filter(|v| v.vote).map(|v| v.stake).sum();
            let rate = stake_approved / total_stake;
            let approved = (rate >= threshold_ratio);

            let reason = if approved {
                format!("DPoS success: {}% >= {}%", (rate*100.0) as u32, (threshold_ratio*100.0) as u32)
            } else {
                format!("DPoS fail: {}% < {}%", (rate*100.0) as u32, (threshold_ratio*100.0) as u32)
            };

            DposResult {
                batch_hash: bv.batch_hash,
                approved,
                total_stake,
                stake_approved,
                approve_rate: rate,
                threshold: threshold_ratio,
                reason,
            }
        })
        .collect()
}
