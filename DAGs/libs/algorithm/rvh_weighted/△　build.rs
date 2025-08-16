fn main() {
    println!("cargo:rerun-if-changed=build.rs");

    // AVX2 / NEON feature を検出して `cfg` に付与
    if std::env::var("CARGO_CFG_TARGET_ARCH").unwrap() == "x86_64"
        && std::is_x86_feature_detected!("avx2")
    {
        println!("cargo:rustc-cfg=has_avx2");
    }
    if std::env::var("CARGO_CFG_TARGET_ARCH").unwrap() == "aarch64"
        && std::is_aarch64_feature_detected!("neon")
    {
        println!("cargo:rustc-cfg=has_neon");
    }
}
