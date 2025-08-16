// D:\city_chain_project\DAGs\libs\algorithm\rvh_weighted\tests\test_basic.rs

// 変更点：rvh_weighted::weighted モジュールから直接インポート
use rvh_weighted::weighted::{NodeInfo, weighted_select};

#[test]
fn basic_top1() {
    let nodes = vec![
        NodeInfo::new("n1", 1000, 8_000, 30.0),
        NodeInfo::new("n2",  200, 1_000, 10.0),
        NodeInfo::new("n3",  600, 4_000, 20.0),
    ];
    let sel = weighted_select(&nodes, "key42", 1).unwrap();
    assert_eq!(sel.len(), 1);
    assert!(nodes.iter().any(|n| n.id == sel[0]));
}

#[test]
fn k_too_large() {
    let nodes = vec![NodeInfo::new("n1", 1, 1, 1.0)];
    assert!(weighted_select(&nodes, "k", 2).is_err());
}
