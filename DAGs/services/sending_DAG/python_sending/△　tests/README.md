D:\city_chain_project\network\DAGs\python\tests\
├── test_integration.py       # システム全体の統合テスト（修正版）
└── test_rust_integration.py  # Python↔Rust連携テスト

前提: Rustコードを pyo3 でビルドし、Python側から import federation_dag できる状態になっている必要があります。

cd D:\city_chain_project\network\DAGs\rust

cargo build --release (あるいは maturin develop / maturin build etc.)

生成された wheel/.dll/.so を Python 環境にインストール / パス設定

その後 pytest を実行

この2つのファイル test_integration.py (統合テスト) と test_rust_integration.py (Python↔Rust連携テスト) によって、動的バッチ + リバランス + 6ヶ月ルール + DPoS を含む全体の流れを、Flaskサーバ起動→HTTPリクエストで統合テスト
Rust側 のrayon並列検証や ntru/dilithium Stub の呼び出しをPythonから行う連携テスト

が検証できるようになります。 これで「本番実装用」に近い形で、フェデレーションDAGの機能が動いているかを一通り試せるはずです。