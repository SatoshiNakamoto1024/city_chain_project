モジュール名、	主担当、	ざっくり役割・実装ポイント、	典型ユースケース
rvh_weighted、	②、	重み付き HRW ( stake / 容量 / RTT を反映 )とSIMD 版スコア計算＋64bit 浮動小数点重み合成	、　DPoS 投票先選定と容量バランシング

rvh_weighted/                       # ── Git サブリポジトリでも可
├─ Cargo.toml
├─ README.md
├─ build.rs                         # “neon/avx2” 検出
└─ src/
   ├─ lib.rs                        # crate 入口
   ├─ weighted.rs                   # コア実装（public）
   ├─ simd_utils.rs                 # AVX2 / NEON fallback
   ├─ main_weighted.rs              # 最小 CLI サンプル
   └─ tests/
      ├─ test_basic.rs              # 単体テスト
      └─ test_error.rs
benches/
└─ bench_weighted.rs                # Criterion ベンチ


修正方法 — rvh_simd に再エクスポートを追加
❶ rvh_simd/src/lib.rs を開いて、末尾に 1 行 足すだけ
//! rvh_simd  ─ SIMD 128-bit ハッシュ

#![warn(missing_docs)]

pub mod simd_hash;

pub use simd_hash::score_u128_simd as score128;   // ★ 追加：外部へ再公開
すでに似た re-export がある場合は、
pub use simd_hash::score_u128_simd as score128; に統一しておけば OK です。


3. 再ビルド＆テスト
# 1) rvh_simd を先にビルドしておく
cd DAGs/libs/algorithm/rvh_simd
cargo build --release

# 2) rvh_weighted をビルド＆テスト
cd ../rvh_weighted
cargo build --release
cargo test


test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests\test_basic.rs (target\debug\deps\test_basic-1612953c82a8b847.exe)

running 2 tests
test k_too_large ... ok
test basic_top1 ... ok

test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests\test_error.rs (target\debug\deps\test_error-66a552d9c6c08c74.exe)

running 3 tests
test k_zero ... ok
test empty_nodes ... ok
test k_too_big ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests rvh_weighted

running 1 test
test src\lib.rs - (line 7) ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.34s


# ベンチ (結果は target/criterion/)
cargo bench -p rvh_weighted


Compiling rvh_weighted v0.1.0 (D:\city_chain_project\DAGs\libs\algorithm\rvh_weighted)
warning: `rvh_weighted` (lib test) generated 2 warnings (2 duplicates)
    Finished `bench` profile [optimized] target(s) in 4.14s
     Running unittests src\lib.rs (target\release\deps\rvh_weighted-faaea96567c64960.exe)

running 2 tests
test tests::basic ... ignored
test tests::serde_roundtrip ... ignored

test result: ok. 0 passed; 0 failed; 2 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running benches\bench_weighted.rs (target\release\deps\bench_weighted-33e1f8b47992a378.exe)
Gnuplot not found, using plotters backend
weighted_select_k5      time:   [145.94 µs 150.14 µs 154.70 µs]
Found 9 outliers among 100 measurements (9.00%)
  7 (7.00%) high mild
  2 (2.00%) high severe
