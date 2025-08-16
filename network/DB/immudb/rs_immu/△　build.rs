use std::env;

fn main() {
    let proto_root = "D:/city_chain_project/proto/schema"; // protoファイルのルートフォルダ

    // プロトファイルが更新されたら再コンパイル
    println!("cargo:rerun-if-changed={}", proto_root);

    tonic_build::configure()
        .build_client(true)  // Rustでクライアントを使う
        .build_server(false) // Rust側ではサーバーを実装しない
        .compile_protos(
            &[
                "D:/city_chain_project/proto/schema/immudb.proto",
            ],
            &[proto_root],
        )
        .expect("Failed to compile protobuf files");
}
