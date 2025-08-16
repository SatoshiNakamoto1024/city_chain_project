// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\tests\test_faultset.rs
use rvh_faultset_rust::error::FaultsetError;
use rvh_faultset_rust::failover;

#[test]
fn empty_nodes() {
    let err = failover(&[], &[], 50.0).unwrap_err();
    assert_eq!(err, FaultsetError::EmptyNodes);
}

#[test]
fn length_mismatch() {
    let nodes = vec!["a".to_string()];
    let lats  = vec![10.0, 20.0];
    let err = failover(&nodes, &lats, 100.0).unwrap_err();
    assert_eq!(err, FaultsetError::LengthMismatch(1, 2));
}

#[test]
fn negative_threshold() {
    let nodes = vec!["a".to_string()];
    let lats  = vec![10.0];
    let err = failover(&nodes, &lats, -1.0).unwrap_err();
    assert_eq!(err, FaultsetError::NegativeThreshold(-1.0));
}

#[test]
fn selection() {
    let nodes = vec!["a".into(), "b".into(), "c".into()];
    let lats  = vec![50.0, 150.0, 75.0];
    let sel   = failover(&nodes, &lats, 100.0).unwrap();
    assert_eq!(sel, vec!["a".to_string(), "c".to_string()]);
}
