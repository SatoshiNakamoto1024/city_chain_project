// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\src\lib.rs
//! Crate entry – re-exports, Python bindings & public API.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic, clippy::nursery)]

pub mod error;
pub mod model;
pub mod holdset;
pub mod metrics;
//  Rust-only ビルドでも通るようにガード
#[cfg(any(feature = "python", feature = "python-ext"))]
pub mod bindings;            // PyO3 glue

#[cfg(feature = "grpc")]
pub mod grpc;

pub use holdset::{calc_score, HoldAggregator};
pub use model::{HoldEvent, HoldStat};

/// Generated gRPC/protobuf types (`package hold` in hold.proto)
pub mod pb {
    tonic::include_proto!("poh"); // パッケージ名と一致させる
    // Reflection 用の FD set（build.rs で生成）
    pub const FILE_DESCRIPTOR_SET: &[u8] =
        tonic::include_file_descriptor_set!("pb_descriptor");
}
