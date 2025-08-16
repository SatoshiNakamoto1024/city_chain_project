// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\src\holdset.rs

//! Core aggregation & high-performance score calculation.
//
// 機能一覧
// ----------------------------------------
// * record()          : 単一 HoldEvent を登録
// * calc_score()      : 任意 Vec<HoldEvent> から合算スコア算出 (並列 Rayon)
// * snapshot()        : DashMap から Vec<HoldStat> をコピー
// * top_n()           : スコア降順に上位 N 件取得
// * spawn_gc_task()   : Tokio タスクで TTL 超過エントリを自動削除
//
// スレッド安全 (DashMap) なので Tokio マルチスレッド / Rayon どちらとも併用できる。

use std::{sync::Arc, time::Duration};
use crate::{error::*, metrics, model::*};
use chrono::{DateTime, Duration as ChronoDuration, Utc};
use dashmap::{mapref::entry::Entry, DashMap};
use rayon::prelude::*;
use tokio::{select, task, time};

/// 保持秒数を計算 & バリデーション
fn seconds_held(ev: &HoldEvent, now: DateTime<Utc>) -> Result<i64> {
    if ev.token_id.is_empty() || ev.holder_id.is_empty() {
        return Err(HoldMetricsError::InvalidField);
    }
    let end = ev.end.unwrap_or(now);
    if end < ev.start {
        return Err(HoldMetricsError::InvalidDuration);
    }
    Ok((end - ev.start).num_seconds())
}

/// 内部保持用 – DashMap の value 型
#[derive(Debug, Clone)]
struct HolderState {
    total_seconds: i64,
    weighted_score: f64,
    updated_at: DateTime<Utc>,
}

impl From<HolderState> for HoldStat {
    fn from(s: HolderState) -> Self {
        Self {
            holder_id: String::new(), // placeholder, 後で外側で埋める
            total_seconds: s.total_seconds,
            weighted_score: s.weighted_score,
            updated_at: s.updated_at,
        }
    }
}

/// Thread-safe aggregator
pub struct HoldAggregator {
    inner: DashMap<String, HolderState>,
    ttl: Option<ChronoDuration>, // None = 無期限
}

impl Default for HoldAggregator {
    fn default() -> Self {
        Self {
            inner: DashMap::new(),
            ttl: None,
        }
    }
}

impl HoldAggregator {
    /// TTL(秒) 付きで新規作成。ttl_secs == 0 なら TTL 無効
    pub fn with_ttl(ttl_secs: u64) -> Self {
        let ttl = if ttl_secs == 0 {
            None
        } else {
            Some(ChronoDuration::seconds(ttl_secs as i64))
        };
        Self {
            inner: DashMap::new(),
            ttl,
        }
    }

    /// 1 件登録（非同期呼出しも可）
    pub fn record(&self, ev: &HoldEvent) -> Result<()> {
        let now = Utc::now();
        let secs = seconds_held(ev, now)?;
        let weight_contrib = secs as f64 * ev.weight;

        match self.inner.entry(ev.holder_id.clone()) {
            Entry::Occupied(mut occ) => {
                let st = occ.get_mut();
                st.total_seconds += secs;
                st.weighted_score += weight_contrib;
                st.updated_at = now;
            }
            Entry::Vacant(vac) => {
                vac.insert(HolderState {
                    total_seconds: secs,
                    weighted_score: weight_contrib,
                    updated_at: now,
                });
            }
        }

        metrics::HOLD_EVENTS.inc();
        metrics::HOLD_SCORE_HISTO.observe(weight_contrib);
        Ok(())
    }

    /// 全 holder のスナップショットを Vec で取得
    pub fn snapshot(&self) -> Vec<HoldStat> {
        self.inner
            .iter()
            .map(|r| {
                let mut stat: HoldStat = r.value().clone().into();
                stat.holder_id = r.key().clone();
                stat
            })
            .collect()
    }

    /// 上位 N 件を weighted_score 降順で返す
    pub fn top_n(&self, n: usize) -> Vec<HoldStat> {
        let mut vec = self.snapshot();
        vec.sort_by(|a, b| b.weighted_score.partial_cmp(&a.weighted_score).unwrap());
        vec.truncate(n);
        vec
    }

    /// TTL を超えたレコードを削除（即時実行）
    pub fn run_gc_once(&self) -> usize {
        let Some(ttl) = self.ttl else { return 0 };
        let now = Utc::now();
        let before = now - ttl;
        let mut removed = 0;
        self.inner.retain(|_, v| {
            let keep = v.updated_at >= before;
            if !keep {
                removed += 1;
            }
            keep
        });
        removed
    }

    /// Tokio task として periodic GC を自動起動
    /// ```rust,no_run
    /// use std::{sync::Arc, time::Duration};
    /// use poh_holdmetrics_rust::holdset::HoldAggregator;
    ///
    /// // 保持イベントを 1 時間 (TTL=3600 秒) で自動 GC する Aggregator
    /// let agg = Arc::new(HoldAggregator::with_ttl(3600));
    ///
    /// // 60 秒ごとに GC を走らせるバックグラウンドタスクを起動
    /// let handle = agg.clone().spawn_gc_task(Duration::from_secs(60));
    ///
    /// // …後で停止したい場合
    /// handle.abort();
    /// ```
    pub fn spawn_gc_task(self: Arc<Self>, interval: Duration) -> task::JoinHandle<()> {
        task::spawn(async move {
            let mut ticker = time::interval(interval);
            loop {
                select! {
                    _ = ticker.tick() => {
                        let removed = self.run_gc_once();
                        if removed > 0 {
                            tracing::debug!(removed, "GC removed expired holders");
                        }
                    }
                }
            }
        })
    }
}

/// Pure 関数 – Vec<HoldEvent> → 合算スコア
pub fn calc_score(events: &[HoldEvent]) -> Result<f64> {
    let now = Utc::now();
    let sum = events
        .par_iter()
        .map(|ev| seconds_held(ev, now).map(|s| s as f64 * ev.weight))
        .collect::<Result<Vec<_>>>()?
        .into_iter()
        .sum();
    Ok(sum)
}
