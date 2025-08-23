// \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\build.rs
use std::{env, path::PathBuf};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // OUT_DIR = $TARGET/build/…/out
    let out_dir = PathBuf::from(env::var("OUT_DIR")?);

    tonic_build::configure()
        // descriptor は OUT_DIR/pb_descriptor.bin に出力
        .file_descriptor_set_path(out_dir.join("pb_descriptor.bin"))
        .build_server(true)                 // サーバ側コードを生成
        .build_client(true)                 // ★ クライアントも生成 ← 追加
        // .out_dir(&out_dir)                // ← 明示しなくても OUT_DIR になるので省略
        .compile(
            &["../poh_holdmetrics_python/poh_holdmetrics/protocols/hold.proto"],
            &["../poh_holdmetrics_python/poh_holdmetrics/protocols"],
        )?;

    // ── PyO3 が自動で python.lib を解決するので追加リンクは不要
    println!("cargo:rerun-if-changed=../poh_holdmetrics_python/poh_holdmetrics/protocols/hold.proto");
    Ok(())
}
