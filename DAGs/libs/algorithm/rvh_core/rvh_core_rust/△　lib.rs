// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\src\lib.rs
// Rendezvous 算法を外部に公開
/// rvh_rust crate root – Python エクスポート & コアロジック
pub mod rendezvous;
pub mod utils;  // ← これが必要！
mod bindings;          // ← #[pymodule] を含む

pub use rendezvous::{rendezvous_hash, RendezvousError};
pub use bindings::*;   // Python ラッパーを re-export