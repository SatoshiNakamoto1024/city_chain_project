use std::env;
use std::path::PathBuf;
use tonic_build;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Define each directory path individually for `PROTOC_INCLUDE`
    let include_paths = vec![
        "D:/city_chain_project/proto/googleapis/google/api",
        "D:/city_chain_project/proto/grpc-gateway/protoc-gen-openapiv2/options",
    ];

    for path in &include_paths {
        println!("cargo:rerun-if-changed={}", path);
    }

    // Set `PROTOC_INCLUDE` to point to each path individually
    for path in include_paths {
        env::set_var("PROTOC_INCLUDE", path);
    }

    // Compile Protocol Buffers using `tonic_build`
    tonic_build::configure()
        .compile(
            &[
                "proto/immudb.proto",
                "proto/googleapis/google/api/annotations.proto",
                "proto/grpc-gateway/protoc-gen-openapiv2/options/openapiv2.proto",
            ],
            &[
                "proto",
                "proto/googleapis",
                "proto/grpc-gateway/protoc-gen-openapiv2/options",
            ],
        )
        .expect("Failed to compile protos");

    Ok(())
}
