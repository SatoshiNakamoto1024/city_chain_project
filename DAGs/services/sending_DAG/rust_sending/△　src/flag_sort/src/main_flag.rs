// sending_DAG\rust_sending\flag_sort\src\main_flag.rs
use flag_rust::sorter::sort_by_flag;
use pyo3::Python;

fn main() {
    Python::with_gil(|py| {
        let tuples = vec![
            ("fresh_tx".into(), py.None()),
            ("checkpoint".into(), py.None()),
            ("poh_ack".into(), py.None()),
        ];
        let pri = vec!["checkpoint".into(), "poh_ack".into(), "fresh_tx".into()];
        let out = sort_by_flag(tuples, pri);
        for (flag, _) in out { println!("{}", flag); }
    });
}
