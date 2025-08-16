// D:\city_chain_project\DAGs\libs\algorithm\rvh_weighted\tests\test_error.rs

//! Error-path unit-tests for rvh_weighted
//!
//! * 空ノードリスト
//! * k == 0
//! * k が n を超える

// 変更点：こちらも weighted モジュールからインポート
use rvh_weighted::weighted::{weighted_select, NodeInfo, WeightError};

fn sample_nodes<'a>() -> Vec<NodeInfo<'a>> {
    vec![
        NodeInfo::new("A", 1_000, 5_000, 12.0),
        NodeInfo::new("B", 2_000, 7_000, 18.0),
    ]
}

#[test]
fn empty_nodes() {
    assert_eq!(
        weighted_select(&[], "key", 1).unwrap_err(),
        WeightError::Empty
    );
}

#[test]
fn k_zero() {
    assert_eq!(
        weighted_select(&sample_nodes(), "key", 0).unwrap_err(),
        WeightError::TooMany(0, 2)
    );
}

#[test]
fn k_too_big() {
    assert_eq!(
        weighted_select(&sample_nodes(), "key", 5).unwrap_err(),
        WeightError::TooMany(5, 2)
    );
}
