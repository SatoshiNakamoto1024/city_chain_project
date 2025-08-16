# フェデレーション・モデルで求められる LDPC 実装ポリシー
| レイヤ                        | 目的                         | 制約                                   | 推奨コード設計                                               |
| -------------------------- | -------------------------- | ------------------------------------ | ----------------------------------------------------- |
| **City-DAG**<br>(≈10 億ノード) | 500 ms 以内で **シャード生成 & 配布** | • 1 RTT 内に完了<br>• ノードの演算能力はまちまち      | *疎度が高い QC-LDPC (PEG 派生)*<br>**dv=3, dc=6**, girth ≥ 8 |
| **Continental-DAG**        | 市レベルの欠損をピア間で補完             | • 欠損 ≤ 5 % なら 200 ms 以内に復元           | 同じ QC 行列だが **BP 反復 8 回**<br>Min-Sum (スケール係数 0.8)      |
| **Global-DAG**             | 深刻な災害時、クロス大陸で復元            | • 欠損 ≤ parity ほぼ限界<br>• 遅延は 1〜2 s 許容 | **BP 反復 20 回 + Early-Stop**<br>失敗時は RS フォールバック        |


QC-PEG (Quasi-Cyclic Progressive Edge Growth) を使う理由
行列 H が 循環ブロックなので SIMD/AVX2 に乗せやすい
行列をブロック単位で送受信でき、ノード分散が容易
PEG の「高い girth」と QC の「実装容易さ」を両取り

Min-Sum（BP 近似）を選ぶ理由
浮動小数点演算を削減⇒モバイル／エッジでも 500 ms 内に収まる
係数 0.8〜0.9 を掛けるだけで誤差がほぼ収束

反復回数
City-DAG: 8 回固定（平均 2〜3 回で収束、最悪 8）
Continental-DAG: 8 回＋早期収束チェック
Global-DAG: 20 回まで許容、収束しなければ RS 再構築

ディレクトリ構成（最終形）
ldpc/
├── Cargo.toml
├── tests/
│   ├── test_city.rs
│   ├── test_continent.rs
│   └── test_global.rs
│        
└── src/
    ├── lib.rs              # 公開 API & ティア毎のプリセット
    ├── gf.rs               # GF(2⁸) 汎用演算
    │
    ├── design/             # H 行列生成
    │   ├── mod.rs
    │   ├── qcpeg.rs        # QC-PEG 実装（推奨）
    │   ├── qc_proto.rs     # QC-プロトグラフ（小ブロック）
    │   └── validate.rs     # girth / rank チェック
    │
    ├── encoder/            # Systematic エンコード
    │   ├── mod.rs
    │   └── sparse_mul.rs   # AVX2/NEON 付き疎行列×ベクトル
    │
    ├── decoder/
    │   ├── mod.rs
    │   ├── peeling.rs      # 欠損のみ高速
    │   ├── min_sum.rs      # Min-Sum BP
    │   └── bp.rs           # 完全 Sum-Product BP
    │
    ├── tiers/              # DAG レイヤごとのプリセット
    │   ├── city.rs         # dv=3, dc=6, iter=8
    │   ├── continent.rs    # iter=8, early_stop
    │   └── global.rs       # iter=20 + fallback
    │
    ├── pipeline/                # ★ 新規 “非同期パイプライン” レイヤ
    │   ├── src/
    │   │   ├── lib.rs        
    │   │   ├── main_pipeline.rs     # bin     
    │   │   ├── stream_encode.rs     # ▷ ❶ バイト列 → `ShardStream`
    │   │   ├── stream_decode.rs     # ▷ ❷ `ShardStream` → 完全復元
    │   │   ├── util.rs              # バッファ pool・CRC32C・BLAKE3 等
    │   │   │
    │   │   ├── sender/              # 送信側ネット I/O
    │   │   │    ├── mod.rs
    │   │   │    ├── quic.rs          # QUIC (quinn) マルチストリーム送信
    │   │   │    └── tcp.rs           # フォールバック TCP / TLS
    │   │   │
    │   │   └── receiver/            # 受信側ネット I/O
    │   │        ├── mod.rs
    │   │        ├── quic.rs
    │   │        └── tcp.rs
    │   │   
    │   ├── tests/
    │   │        └── test_pipeline.rs     # End-to-end async ↔︎ network
    │   │ 
    │   └── Cargo.toml
    │
    └── bench/
        ├── bench_city.rs
        └── bench_global.rs
        

各ファイルの役割
ファイル	主な関数／型	説明
design/qcpeg.rs	fn generate(k,m,blk)	PEG で生成→QC ブロック (circulant shift) に変換
encoder/sparse_mul.rs	fn parity(A, data)	CRS 形式で A * data を SIMD 並列化
decoder/peeling.rs	fn decode_erasure()	欠損ノードを逐次単純連立で除去
decoder/min_sum.rs	MinSumDecoder::decode(max_iter, scale)	水平／垂直パス更新を i8 / f32 で実装
tiers/city.rs	pub const PROFILE	行列パラメータ + 反復数 + アルゴ切替
tests/test_city.rs	1000 ランダム欠損	500 ms 以内 & 正確復元を assert
bench/bench_city.rs	Criterion	encode/decode スループット測定

実装順（おすすめ）
gf.rs 切り出し（既存の matrix.rs から演算部を移動）

design/qcpeg.rs：

PEG (dv=3, dc=6) で骨格グラフ → ブロックサイズ 32〜64 byte で QC 化

validate::check_girth(&H) >= 8 を満たすまでリトライ

encoder/sparse_mul.rs：

1 ブロック単位 (32 byte) の XOR + 1 ビットシフトでパリティ計算

rayon & AVX2 で行レベル parallel

decoder/min_sum.rs：

8 反復固定 → 収束チェック (syndrome == 0)

scale=0.8 で Min-Sum 更新

tiers/city.rs にプリセット定義し、LDPCEncoder::with_tier(Tier::City) が選べるように

tests/test_city.rs：

欠損率 0〜m / 3 を proptest でランダム生成

bench で 100 MiB/s 以上を確認

Continental & Global tier は反復数／行列サイズだけ変えて再利用

まとめ
QC-PEG + Min-Sum は市レベル (10 億ノード) でも
パリティ生成 ≤ 500 ms, 欠損 5 % 復元 ≤ 200 ms を現実的に達成可能。

行列設計 → エンコード → Min-Sum BP の 3 ステップを
上記ファイル構成で分離すれば、あとから行列だけ差し替えても
DAG レイヤごとの要件に合わせて容易にチューニングできます。

次に QC-PEG 行列ジェネレータ から着手する場合は、design/qcpeg.rs の
雛形コードとテスト用 YAML protograph 例を提示しますので、
必要ならリクエストしてください！


# まとめ
AVX2／NEON が有効なターゲットでは自動的に SIMD コードが採用され、
不所持 CPU では安全にスカラーパスへフォールバックします。

これにより City ティア で
エンコード: 数百 MiB/s・欠損復元 (peeling) ≤ 200 ms が狙えます。

高精度 BP が必要な Continental / Global ティアは bp.rs（Sum-Product）で
max_iter 20, scale 1.0 を指定してください。

さらに テスト／ベンチコード の充実や
クロスコンパイル (Android/ARMv8) 向け調整が必要な場合は、
次のステップとしてご相談ください！

