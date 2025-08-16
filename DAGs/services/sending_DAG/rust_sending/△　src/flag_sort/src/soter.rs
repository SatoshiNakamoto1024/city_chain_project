// sending_DAG\rust_sending\flag_sort\src\soter.rs
use pyo3::prelude::*;
use rayon::prelude::*;

#[pyfunction]
pub fn sort_by_flag(tuples: Vec<(String, pyo3::PyObject)>, priority: Vec<String>)
                    -> Vec<(String, pyo3::PyObject)> {
    // priority の index をマップ化
    use std::collections::HashMap;
    let mut pri = HashMap::new();
    for (i, p) in priority.iter().enumerate() { pri.insert(p, i); }

    let mut v = tuples;
    v.par_sort_unstable_by(|a, b| {
        let ia = pri.get(&a.0).copied().unwrap_or(priority.len());
        let ib = pri.get(&b.0).copied().unwrap_or(priority.len());
        ia.cmp(&ib)
    });
    v
}
