// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\configs.rs
//! アプリケーション設定の読み込み・バリデーション
use serde::Deserialize;
use std::{fs, path::Path};
use thiserror::Error;

/// ティアごとの分散ポリシー
#[derive(Debug, Deserialize, Clone)]
pub struct TierConfig {
    pub name: String,
    pub weight: usize,
    pub timeout_ms: u64,
    pub parallelism: usize,
    pub retention_days: u32,
}

/// アプリケーション設定全体
#[derive(Debug, Deserialize)]
pub struct Config {
    #[serde(default = "Config::default_data_shards")]
    pub data_shards: usize,
    #[serde(default = "Config::default_parity_shards")]
    pub parity_shards: usize,
    #[serde(default = "Config::default_max_total_shards")]
    pub max_total_shards: usize,

    #[serde(default = "Config::default_async_enabled")]
    pub async_enabled: bool,
    #[serde(default = "Config::default_concurrency")]
    pub concurrency: usize,
    #[serde(default = "Config::default_max_shard_size_bytes")]
    pub max_shard_size_bytes: usize,

    #[serde(default = "Config::default_mongodb_url")]
    pub mongodb_url: String,
    #[serde(default = "Config::default_mongodb_db")]
    pub mongodb_db: String,
    #[serde(default = "Config::default_mongodb_collection")]
    pub mongodb_collection: String,
    #[serde(default = "Config::default_retention_days")]
    pub retention_days: u32,

    #[serde(default = "Config::default_metrics_enabled")]
    pub metrics_enabled: bool,
    #[serde(default = "Config::default_report_interval_seconds")]
    pub report_interval_seconds: u64,

    /// 地理ティアごとの分散ポリシー
    #[serde(default)]
    pub distribution: DistributionConfig,
}

/// distribution セクション
#[derive(Debug, Deserialize)]
pub struct DistributionConfig {
    #[serde(default)]
    pub tiers: Vec<TierConfig>,
}

impl Default for DistributionConfig {
    fn default() -> Self {
        DistributionConfig { tiers: Vec::new() }
    }
}

impl Default for Config {
    fn default() -> Self {
        Config {
            data_shards: Self::default_data_shards(),
            parity_shards: Self::default_parity_shards(),
            max_total_shards: Self::default_max_total_shards(),
            async_enabled: Self::default_async_enabled(),
            concurrency: Self::default_concurrency(),
            max_shard_size_bytes: Self::default_max_shard_size_bytes(),
            mongodb_url: Self::default_mongodb_url(),
            mongodb_db: Self::default_mongodb_db(),
            mongodb_collection: Self::default_mongodb_collection(),
            retention_days: Self::default_retention_days(),
            metrics_enabled: Self::default_metrics_enabled(),
            report_interval_seconds: Self::default_report_interval_seconds(),
            distribution: DistributionConfig::default(),
        }
    }
}

impl Config {
    fn default_data_shards() -> usize { 4 }
    fn default_parity_shards() -> usize { 2 }
    fn default_max_total_shards() -> usize { 32 }
    fn default_async_enabled() -> bool { true }
    fn default_concurrency() -> usize { 4 }
    fn default_max_shard_size_bytes() -> usize { 1 << 20 }
    fn default_mongodb_url() -> String { "mongodb://localhost:27017".into() }
    fn default_mongodb_db() -> String { "ec_shards".into() }
    fn default_mongodb_collection() -> String { "shard_data".into() }
    fn default_retention_days() -> u32 { 180 }
    fn default_metrics_enabled() -> bool { true }
    fn default_report_interval_seconds() -> u64 { 60 }

    /// TOML からロード
    pub fn load_from<P: AsRef<Path>>(path: P) -> Result<Self, ConfigError> {
        let p = path.as_ref();
        let mut cfg = if p.exists() {
            let s = fs::read_to_string(p).map_err(|e| ConfigError::Io(p.display().to_string(), e))?;
            toml::from_str(&s).map_err(|e| ConfigError::Parse(p.display().to_string(), e.to_string()))?
        } else {
            Config::default()
        };
        cfg.validate()?;
        Ok(cfg)
    }

    /// 制約チェック
    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.data_shards == 0 {
            return Err(ConfigError::InvalidValue("data_shards must be >=1".into()));
        }
        if self.parity_shards == 0 {
            return Err(ConfigError::InvalidValue("parity_shards must be >=1".into()));
        }
        let total = self.data_shards + self.parity_shards;
        if total > self.max_total_shards {
            return Err(ConfigError::InvalidValue(format!(
                "total shards ({}) > max_total_shards ({})", total, self.max_total_shards
            )));
        }
        if self.concurrency == 0 {
            return Err(ConfigError::InvalidValue("concurrency must>=1".into()));
        }
        if self.max_shard_size_bytes == 0 {
            return Err(ConfigError::InvalidValue("max_shard_size_bytes must>=1".into()));
        }
        if self.mongodb_url.trim().is_empty() {
            return Err(ConfigError::InvalidValue("mongodb_url cannot be empty".into()));
        }
        if self.mongodb_db.trim().is_empty() {
            return Err(ConfigError::InvalidValue("mongodb_db cannot be empty".into()));
        }
        if self.mongodb_collection.trim().is_empty() {
            return Err(ConfigError::InvalidValue("mongodb_collection cannot be empty".into()));
        }
        if self.retention_days == 0 {
            return Err(ConfigError::InvalidValue("retention_days must>=1".into()));
        }
        if self.metrics_enabled && self.report_interval_seconds == 0 {
            return Err(ConfigError::InvalidValue(
                "report_interval_seconds >=1 when metrics_enabled".into()
            ));
        }
        // ティア検証
        for tier in &self.distribution.tiers {
            if tier.name.trim().is_empty() {
                return Err(ConfigError::InvalidValue("tier.name cannot be empty".into()));
            }
            if tier.weight == 0 {
                return Err(ConfigError::InvalidValue(format!(
                    "tier '{}' weight must>=1", tier.name
                )));
            }
            if tier.timeout_ms == 0 || tier.timeout_ms > 1000 {
                return Err(ConfigError::InvalidValue(format!(
                    "tier '{}' timeout_ms out of range", tier.name
                )));
            }
            if tier.parallelism == 0 {
                return Err(ConfigError::InvalidValue(format!(
                    "tier '{}' parallelism>=1", tier.name
                )));
            }
            if tier.retention_days == 0 {
                return Err(ConfigError::InvalidValue(format!(
                    "tier '{}' retention_days>=1", tier.name
                )));
            }
        }
        Ok(())
    }
}

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("I/O error reading `{0}`: {1}")]
    Io(String, #[source] std::io::Error),
    #[error("Parse error in `{0}`: {1}")]
    Parse(String, String),
    #[error("Invalid configuration: {0}")]
    InvalidValue(String),
}
