// D:\city_chain_project\Algorithm\EC\ec_rust_src\tests\test_config.rs
#![cfg(feature = "configs_only")]

use ec_rust_src::configs::{Config, ConfigError, Replication};
use std::env;
use std::fs;

const TMP_CONF: &str = "tests/tmp_config.toml";

/// デフォルト値だけでロードできるか
#[test]
fn load_default() {
    let cfg = Config::default();
    assert_eq!(cfg.data.shard_size, 1024);
    assert_eq!(cfg.data.data_shards, 10);
    assert_eq!(cfg.storage.retention_days, 180);
    assert_eq!(cfg.storage.replication, Replication::Continental);
    assert_eq!(cfg.performance.timeout_ms, 500);
}

/// ファイルから正しくロードできるか
#[test]
fn load_from_file() {
    let content = r#"
        [data]
        shard_size = 2048
        data_shards = 5
        parity_shards = 2
        [storage]
        retention_days = 90
        replication = "global"
        [performance]
        timeout_ms = 250
    "#;
    fs::write(TMP_CONF, content).unwrap();
    let cfg = Config::load(TMP_CONF).unwrap();
    assert_eq!(cfg.data.shard_size, 2048);
    assert_eq!(cfg.data.data_shards, 5);
    assert_eq!(cfg.storage.retention_days, 90);
    assert_eq!(cfg.storage.replication, Replication::Global);
    assert_eq!(cfg.performance.timeout_ms, 250);
    fs::remove_file(TMP_CONF).unwrap();
}

/// 異常系：shard_size=0 は弾かれる
#[test]
fn zero_shard_size() {
    let content = r#"
        [data]
        shard_size = 0
        data_shards = 3
        parity_shards = 1
    "#;
    fs::write(TMP_CONF, content).unwrap();
    let err = Config::load(TMP_CONF).unwrap_err();
    match err {
        ConfigError::Validation(msg) => assert!(msg.contains("shard_size")),
        _ => panic!("expected Validation error"),
    }
    fs::remove_file(TMP_CONF).unwrap();
}

/// 異常系：data_shards=0 は弾かれる
#[test]
fn zero_data_shards() {
    let content = r#"
        [data]
        shard_size = 256
        data_shards = 0
        parity_shards = 1
    "#;
    fs::write(TMP_CONF, content).unwrap();
    let err = Config::load(TMP_CONF).unwrap_err();
    match err {
        ConfigError::Validation(msg) => assert!(msg.contains("data_shards")),
        _ => panic!("expected Validation error"),
    }
    fs::remove_file(TMP_CONF).unwrap();
}

/// 異常系：parity_shards=0 は弾かれる
#[test]
fn zero_parity_shards() {
    let content = r#"
        [data]
        shard_size = 256
        data_shards = 3
        parity_shards = 0
    "#;
    fs::write(TMP_CONF, content).unwrap();
    let err = Config::load(TMP_CONF).unwrap_err();
    match err {
        ConfigError::Validation(msg) => assert!(msg.contains("parity_shards")),
        _ => panic!("expected Validation error"),
    }
    fs::remove_file(TMP_CONF).unwrap();
}
