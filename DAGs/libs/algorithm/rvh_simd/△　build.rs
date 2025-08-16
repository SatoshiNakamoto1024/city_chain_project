// D:\city_chain_project\DAGs\libs\algorithm\rvh_simd\build.rs
// build.rs
fn main() {
    // AVX2 / NEON 有無をコンパイル時に環境変数へ
    if std::is_x86_feature_detected!("avx2") {
        println!("cargo:rustc-cfg=feature=\"avx2\"");
    }
    if std::is_aarch64_feature_detected!("neon") {
        println!("cargo:rustc-cfg=feature=\"neon\"");
    }
}
