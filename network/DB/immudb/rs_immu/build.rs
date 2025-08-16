use std::env;

fn main() {
    // proto ファイルのルートパス（環境に合わせて調整してください）
    let proto_root = "D:/city_chain_project/proto/schema";

    // プロトファイルが更新されたら再コンパイル
    println!("cargo:rerun-if-changed={}", proto_root);

    tonic_build::configure()
        .build_client(true)  // Rust でクライアントを使う
        .build_server(false) // サーバー側は Python なので不要
        .compile_protos(
            &[
                "D:/city_chain_project/proto/schema/immudb.proto",
            ],
            &[proto_root],
        )
        .expect("Failed to compile protobuf files");
}
