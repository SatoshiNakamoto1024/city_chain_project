//sending_DAG/rust_sending/dag_core/src/lib.rs

/*!
lib.rs (修正版)

- オブジェクト依存解決 (object_dependency.rs) の呼び出し関数
- DPoS並列集計 (dpos_parallel.rs) の呼び出し関数
- 既存の batch_verify(NTRU/Dilithium) と合わせて Python側が呼べるようにする
*/

use pyo3::prelude::*;
use pyo3::types::{PyAny, PyList};
use serde::{Deserialize, Serialize};

mod ntru_dilithium;
mod object_dependency;
mod dpos_parallel;

use rayon::prelude::*; // 既存

//----------------------------------------------
// 既存の TxItem (簡易)
//----------------------------------------------
#[derive(Serialize, Deserialize, Debug)]
pub struct TxItem {
    pub tx_id: String,
    pub sender: String,
    pub receiver: String,
    pub amount: f64,
    pub hash: String,
    #[serde(default)]
    pub tx_type: String,
}

//----------------------------------------------
// RustDAGApi
//----------------------------------------------
/// Python向けエクスポート
#[pyclass]
struct RustDAGApi {}

#[pymethods]
impl RustDAGApi {
    #[new]
    fn new() -> Self {
        RustDAGApi {}
    }

    /// 1) 署名検証 (ダミー). Python => batch_list => we do parallel filter
    #[text_signature = "(self, batch_list)"]
    fn batch_verify(&self, py: Python, batch_list: &PyAny) -> PyResult<PyObject> {
        let items: Vec<serde_json::Value> = batch_list.extract()?;
        // ここではntru/dilithium stub => 全Tx通す
        // 実際にはparallel check
        // Return same items
        Ok(PyList::new(py, &items).into())
    }

    /// 2) オブジェクト依存 (Sui風)
    #[text_signature = "(self, tx_list, obj_map)"]
    fn resolve_object_deps(&self, py: Python, tx_list: &PyAny, obj_map: &PyAny) -> PyResult<PyObject> {
        let items: Vec<object_dependency::ObjDepTx> = tx_list.extract()?;
        let omap: object_dependency::ObjectMap = obj_map.extract()?;
        let result = object_dependency::resolve_object_dependencies(items, omap);
        // pythonに返す => [ResolveResult]
        Ok(PyList::new(py, &[result])?.into())
    }

    /// 3) DPoS並列承認
    #[text_signature = "(self, vote_lists, threshold)"]
    fn dpos_parallel_collect(&self, py: Python, vote_lists: &PyAny, threshold: f64) -> PyResult<PyObject> {
        let votes: Vec<dpos_parallel::DposBatchVotes> = vote_lists.extract()?;
        let results = dpos_parallel::parallel_dpos_collect(votes, threshold);
        // => pythonに返す => List<DposResult>
        Ok(PyList::new(py, &results).into())
    }

    /// stub: ntru/dilithium
    #[text_signature = "(self, message)"]
    fn ntru_encrypt_stub(&self, message: String) -> PyResult<String> {
        Ok(ntru_dilithium::ntru_encrypt_stub(&message))
    }
    #[text_signature = "(self, ciphertext)"]
    fn ntru_decrypt_stub(&self, ciphertext: String) -> PyResult<String> {
        Ok(ntru_dilithium::ntru_decrypt_stub(&ciphertext))
    }
    fn dilithium_sign_stub(&self, data: String) -> PyResult<String> {
        Ok(ntru_dilithium::dilithium_sign_stub(&data))
    }
    fn dilithium_verify_stub(&self, data: String, signature: String) -> PyResult<bool> {
        Ok(ntru_dilithium::dilithium_verify_stub(&data, &signature))
    }
}

#[pymodule]
fn federation_dag(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustDAGApi>()?;
    m.add("__version__", "0.4.0")?;
    Ok(())
}