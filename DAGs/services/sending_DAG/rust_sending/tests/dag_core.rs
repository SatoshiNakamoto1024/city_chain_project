// sending_DAG\rust_sending\tests\dag_core.rs
use federation_dag::dpos_parallel::{DposValidator, DposBatchVotes, parallel_dpos_collect};

#[test]
fn dpos_threshold() {
    let votes = vec![DposBatchVotes {
        batch_hash: "deadbeef".into(),
        validators: vec![
            DposValidator{validator_id:"A".into(),stake:60.0,online:true,vote:true},
            DposValidator{validator_id:"B".into(),stake:40.0,online:true,vote:false},
        ],
    }];
    let res = parallel_dpos_collect(votes, 0.66);
    assert!(!res[0].approved);
}
