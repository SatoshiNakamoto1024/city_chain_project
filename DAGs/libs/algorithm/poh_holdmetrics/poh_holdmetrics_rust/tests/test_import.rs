// \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\tests\test_import.rs
//! ライブラリがリンク不整合なく import できるか
#[test]
fn crate_imports() {
    let score = poh_holdmetrics_rust::calc_score(&[]).unwrap();
    assert_eq!(score, 0.0);
}
