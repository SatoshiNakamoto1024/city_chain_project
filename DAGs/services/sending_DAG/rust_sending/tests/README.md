rust/
└─ tests/
   ├─ cert_pqc.rs        ← PEM 解析・署名検証 stub
   └─ dag_core.rs        ← object_dependency / dpos_parallel

unit テスト例 dag_core.rs
use federation_dag::dpos_parallel::{DposValidator, DposBatchVotes, parallel_dpos_collect};

#[test]
fn dpos_threshold() {
    let votes = vec![DposBatchVotes {
        batch_hash: "deadbeef".into(),
        validators: vec![
            DposValidator{validator_id:"A".into(),stake:60.0,online:true,vote:true},
            DposValidator{validator_id:"B".into(),stake:40.0,online:true,vote:false},
        ],
    }];
    let res = parallel_dpos_collect(votes, 0.66);
    assert!(!res[0].approved);
}
cargo test --workspace で３ crate 全部まとめて回ります。

🧑‍💻 解説：なぜこの整理か？
目的	整理指針
maturin ビルドを楽に	“crate=Pythonモジュール” に揃え、cdylib で出力。
再利用しやすい API	cert / dag_core / flag という “役割” で分離。ヘッダの import 循環も回避。
CI/CD	workspace なので cargo check, cargo test, maturin build が１コマンドで。
型安全 & 並列化	rayon・serde に集中させ、Python 側はただ呼ぶだけ。
typo バグ削減	valifier→verifier, soter→sorter など即 crash を防止。

📌 次の TODO
proto/storage.proto を定義し、tonic or grpcio で Rust 側 gRPC Stub も準備

NTRU・Dilithium の本実装導入（pqcrypto など or C FFI）

CI Workflow: Linux/macOS/Win で wheels を自動 publish

Bench (cargo criterion) で batch_verify & deps_resolve が 100 µs/tx を切るか確認

「この構成で OK / 修正してほしい箇所 / 次に書き出してほしい具体ファイル」があれば教えてください！