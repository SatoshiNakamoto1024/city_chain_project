// D:\city_chain_project\Algolithm\DPoS\dpos_rust\dpos_consensus.rs
// ポイント:2段階投票: prevote + precommit → precommit=true の stake を最終集計
// suspicious_list: prevote=true なのに precommit=false の validator → Python 側でrecord_double_sign などに使う

use serde::{Serialize, Deserialize};
use rayon::prelude::*;

/*!
dpos_consensus.rs (multi-phase example)

- 2段階投票: prevote => precommit
- suspicious_list: ダブルサイン or contradictory vote => pythonで監視
*/

#[derive(Serialize, Deserialize, Debug)]
pub struct DposValidator {
    pub rep_id: String,
    pub stake: f64,
    pub online: bool,
    pub prevote: bool,   // first round
    pub precommit: bool  // second round
}

#[derive(Serialize, Deserialize, Debug)]
pub struct DposBatch {
    pub batch_hash: String,
    pub validators: Vec<DposValidator>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct DposResult {
    pub batch_hash: String,      // 対象バッチの識別子
    pub approved: bool,          // 承認されたかどうか
    pub reason: String,          // 承認/拒否の理由
    pub suspicious_list: Vec<String>,  // 投票結果に矛盾があった代表者のIDリスト（例：prevoteとprecommitが矛盾）
    pub total_stake: f64,        // オンラインな代表者全体のステーク合計
    pub stake_approve: f64,      // precommitがtrue の代表者のステーク合計
    pub ratio: f64,              // stake_approve / total_stake
}

/// マルチフェーズ投票によるDPoS合意を並列計算する関数
pub fn multi_phase_dpos(batches: Vec<DposBatch>, threshold: f64) -> Vec<DposResult> {
    batches.into_par_iter().map(|batch| {
        // オンラインな代表者のみ抽出
        let online: Vec<&DposValidator> = batch.validators.iter()
            .filter(|v| v.online)
            .collect();
        let total_stake: f64 = online.iter().map(|v| v.stake).sum();
        if total_stake <= 0.0 {
            return DposResult {
                batch_hash: batch.batch_hash,
                approved: false,
                reason: "No online stake available".into(),
                suspicious_list: Vec::new(),
                total_stake: 0.0,
                stake_approve: 0.0,
                ratio: 0.0,
            };
        }
        // 疑わしい代表者の検出：prevoteがtrueなのにprecommitがfalseの場合を検出
        let mut suspicious = Vec::new();
        for v in &online {
            if v.prevote && !v.precommit {
                suspicious.push(v.rep_id.clone());
            }
        }
        // precommitがtrueの代表者のステーク合計
        let stake_approve: f64 = online.iter().filter(|v| v.precommit).map(|v| v.stake).sum();
        let ratio = stake_approve / total_stake;
        let approved = ratio >= threshold;
        let reason = if approved {
            format!("Approved: precommit stake ratio {:.2} meets threshold {:.2}", ratio, threshold)
        } else {
            format!("Rejected: precommit stake ratio {:.2} below threshold {:.2}", ratio, threshold)
        };
        DposResult {
            batch_hash: batch.batch_hash,
            approved,
            reason,
            suspicious_list: suspicious,
            total_stake,
            stake_approve,
            ratio,
        }
    }).collect()
}
