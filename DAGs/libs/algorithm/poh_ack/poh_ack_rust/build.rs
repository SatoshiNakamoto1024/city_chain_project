// build.rs (poh_ack_rust のルートに置く)

fn main() {
    // メインクレートで --features python を付けたときにだけ実行
    if std::env::var("CARGO_FEATURE_PYTHON_EMBED").is_ok() {
        // pyo3-build-config が見つけた libpython をリンクするフラグを cargo に渡す
        pyo3_build_config::add_extension_module_link_args();
    }
}
