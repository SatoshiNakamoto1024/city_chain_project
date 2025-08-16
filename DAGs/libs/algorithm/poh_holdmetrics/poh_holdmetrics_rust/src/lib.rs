// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\src\lib.rs
//! Crate entry – re-exports, Python bindings & public API.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic, clippy::nursery)]

pub mod error;
pub mod model;
pub mod holdset;
pub mod metrics;

// PyO3 バインディング（拡張モジュール）
// ※ 拡張モジュールの初期化で Python API を触るコードは bindings.rs にも置かないこと！
#[cfg(any(feature = "python", feature = "py-ext"))]
pub mod bindings;

#[cfg(feature = "grpc")]
pub mod grpc;

pub use holdset::{calc_score, HoldAggregator};
pub use model::{HoldEvent, HoldStat};

/// Generated gRPC/protobuf types (`package poh` in hold.proto)
pub mod pb {
    tonic::include_proto!("poh"); // パッケージ名と一致
    /// Reflection 用の FileDescriptorSet（build.rs で生成）
    pub const FILE_DESCRIPTOR_SET: &[u8] =
        tonic::include_file_descriptor_set!("pb_descriptor");
}
