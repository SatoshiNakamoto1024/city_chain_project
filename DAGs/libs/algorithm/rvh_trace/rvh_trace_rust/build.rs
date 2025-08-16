// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\build.rs
// build.rs  ―  “拡張モジュール” をビルドするときに
// pyo3 が必要とする cfg / リンクオプションを自動で渡すだけ。
// プロジェクト固有のロジックは一切ありません。

fn main() {
    // 1) cfg(pyo3) / cfg(Py_3_12) などを Rust コンパイラへ転送
    pyo3_build_config::use_pyo3_cfgs();

    // 2) OS 別に適切なリンクフラグを emit
    //
    //    * Linux   :  -lpython3.12
    //    * macOS   :  -undefined dynamic_lookup
    //    * Windows :  python312.lib
    //
    //  abi3‑py312 を使う限り、ここは pyo3 に任せるのが最も安全
    //  （手動で書くと OS や CI の違いで壊れやすい）
    pyo3_build_config::add_extension_module_link_args();
}
