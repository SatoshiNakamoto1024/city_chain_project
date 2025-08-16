// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\src\rendezvous.rs

/// rendezvous.rs ― Rendezvous / HRW (Highest-Random-Weight) Hashing Core
/// ====================================================================
/// * **決定論的** : 同じ入力 → いつでも同じ出力  
/// * **安定性**   : ノード追加／削除時の再配置は最小限  
/// * **速度**     : 1 ノードあたり *O(1)* でハッシュ計算・上位 *k* 抽出  
///
/// # 公開 API
///
/// | 関数                                   | 説明                                        |
/// |----------------------------------------|---------------------------------------------|
/// | [`rendezvous_hash`]                    | **同期版** – 上位 *k* ノードを返す          |
/// | [`rendezvous_hash_async`]              | **非同期版** – Tokio `spawn_blocking` ラッパ |
/// | [`rendezvous_scores`]                  | 各ノードのスコアを列挙（デバッグ／可視化） |
///
/// ここでは **`String` ノード ID** を扱いますが、パフォーマンス要件に応じ  
/// `&[u8]` などへ一般化するのも容易です。
use crate::utils;
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Rendezvous ハッシュが返すエラー
#[derive(Debug, Error, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[non_exhaustive]
pub enum RendezvousError {
    /// `nodes` が空
    #[error("nodes list is empty")]
    NoNodes,
    /// `k` がノード数を超過
    #[error("requested k ({0}) exceeds node count ({1})")]
    TooMany(usize, usize),
}

/// (node, score) タプルを保持するデバッグ用レコード
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ScoredNode<'a> {
    /// ノード ID
    pub node: &'a str,
    /// 128-bit HRW スコア（big-endian）
    pub score: u128,
}

// ---------------------------------------------------------------------
// ▼ 内部共通：スコア列挙
// ---------------------------------------------------------------------

/// すべてのノードについて HRW スコアを計算して返す。  
/// **戻り値はソートされていません。**
#[inline]
pub fn rendezvous_scores<'a>(nodes: &'a [String], key: &str) -> Vec<ScoredNode<'a>> {
    nodes
        .iter()
        .map(|n| ScoredNode {
            node: n,
            score: utils::score_u128(n, key),
        })
        .collect()
}

// ---------------------------------------------------------------------
// ▼ パブリック：同期版 Top-k 抽出
// ---------------------------------------------------------------------

/// 与えられた `nodes` から HRW スコア降順で **上位 `k` ノード** を返す。
///
/// * `nodes` – ノード ID のスライス  
/// * `key`   – オブジェクト／パーティションなどのキー  
/// * `k`     – 返す件数  
///
/// # 戻り値
/// * `Ok(Vec<String>)` – ノード ID をスコア降順で並べたリスト  
/// * `Err(RendezvousError)` – 入力不正
pub fn rendezvous_hash(
    nodes: &[String],
    key: &str,
    k: usize,
) -> Result<Vec<String>, RendezvousError> {
    if nodes.is_empty() {
        return Err(RendezvousError::NoNodes);
    }
    if k > nodes.len() {
        return Err(RendezvousError::TooMany(k, nodes.len()));
    }

    // -------- スコア計算 --------
    let mut scored = rendezvous_scores(nodes, key);

    // -------- 部分ソート --------
    //
    // * k ≪ n を想定し、`select_nth_unstable_by` で O(n) パーティション。
    // * 取り出した k 件のみ安定ソートして確定順序に。
    //
    let (top, _) = scored.split_at_mut(k);
    top.select_nth_unstable_by(k - 1, |a, b| b.score.cmp(&a.score));
    top.sort_by(|a, b| {
        b.score.cmp(&a.score).then(b.node.cmp(&a.node))  // ここを追加！
    });

    Ok(top.iter().map(|s| s.node.to_string()).collect())
}

// ---------------------------------------------------------------------
// ▼ パブリック：非同期版 (Tokio)
// ---------------------------------------------------------------------

/// Tokio ランタイムで **blocking** に計算する非同期ラッパ。
///
/// バインディング側で `ensure_tokio_runtime()` を呼んでおけば
/// Python からの呼び出しでも安全に並列化できます。
pub async fn rendezvous_hash_async(
    nodes: Vec<String>,
    key: String,
    k: usize,
) -> Result<Vec<String>, RendezvousError> {
    tokio::task::spawn_blocking(move || rendezvous_hash(&nodes, &key, k))
        .await
        .expect("spawn_blocking panicked")
}
