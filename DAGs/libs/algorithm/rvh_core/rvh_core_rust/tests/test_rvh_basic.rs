// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\tests\test_rvh_basic.rs
//! Pure-Rust ユニットテスト

use rvh_core_rust::rendezvous::{rendezvous_hash, RendezvousError};

#[test]
fn basic_selection() {
    let nodes = vec!["n1".into(), "n2".into(), "n3".into()];
    let sel   = rendezvous_hash(&nodes, "object-1", 2).unwrap();
    assert_eq!(sel.len(), 2);

    // 冪等性
    let sel2 = rendezvous_hash(&nodes, "object-1", 2).unwrap();
    assert_eq!(sel, sel2);
}

#[test]
fn empty_nodes() {
    let err = rendezvous_hash(&[], "key", 1).unwrap_err();
    matches!(err, RendezvousError::NoNodes);
}

#[test]
fn k_too_large() {
    let nodes = vec!["a".into()];
    let err = rendezvous_hash(&nodes, "key", 2).unwrap_err();
    matches!(err, RendezvousError::TooMany(_, _));
}
