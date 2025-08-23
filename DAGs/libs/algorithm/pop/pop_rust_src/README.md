D:\city_chain_project\Algorithm\PoP\
├── pyproject.toml
├── pop_python\
│   ├── __init__.py
│   ├── events.py
│   ├── localization.py
│   ├── polygons.py
│   └── manager.py
└── pop_rust\
    ├── Cargo.toml
    └── src\
        ├── lib.rs
        ├── types.rs
        ├── polygons.rs
        └── events.rs


Rust バイナリをビルドして動作確認
cd Algorithm/PoP/pop_rust
cargo update
cargo build --release

cargo run --bin main_pop -- query 35.02 139.02
単体テストを実行

cd Algorithm/PoP/pop_rust
cargo test


# ポイント解説
load_polygons：Rust 側に手動定義の PolyItem リストを渡して空間インデックスを構築。
query_point(lat, lon)：ツリー検索＋厳密判定で特定の city_id または None を返す。
check_city_event / check_location_event：ポリゴンに基づくイベント倍率ロジックを Rust 化。
load_polygons_from_dir(path)：polygon_data 内の .geojson ファイルをすべて読み込み、ポリゴンを登録する関数（パス文字列指定）。

test_load_and_query_geojson_directory：ファイルシステム経由の動的ロード機構を確認し、実際に "kanazawa", "paris", そして領域外検証を網羅。

これで Rust 側の PoP アルゴリズム全機能を CI で確実にテストできるようになります。


■　Rust で 「ライブラリ ＋ 複数バイナリ」 を置く時の “３つのルール”
#	ルール	典型ファイル	ひと言で
1	src/lib.rs が “ライブラリ crate” のルート
ここで pub mod … を宣言し 外に公開 する。	src/lib.rs	公開扉

2	src/bin/*.rs は “バイナリ crate”
それぞれ 独立した crate としてコンパイルされる。
ライブラリを呼びたければ パッケージ名 で参照。	src/bin/main_pop.rs	姉妹 crate

3	Cargo.toml に [lib] name = "…" を必ず書く
バイナリから use pop_rust::… するための “識別子”。	Cargo.toml	見つけてもらう名札

まとめ：今後のRustプロジェクト構成の鉄則
状況	必須の書き方
src/lib.rs 経由で呼びたい	pub mod xxx; を lib.rs に記述
src/bin/*.rs にある場合	use crate::xxx; は使えない、lib経由必須
mod xxx; を使うなら	同じディレクトリに xxx.rs が必要

    └── pop_rust/
        ├── Cargo.toml
        ├── src/
        │   ├── lib.rs               ← pub mod types; などあり
        │   ├── types.rs
        │   ├── main_pop.rs
        │   ├── polygons.rs
        │   └── events.rs
        └── tests/
            └── test_pop.rs         ← use pop_rust::types::PolyItem; などOK

✅ Testエラーの解決策A（おすすめ）
Cargo.toml に [lib] セクションを追加：
[lib]
name = "pop_rust"
path = "src/lib.rs"

そしてこのまま tests/test_pop.rs を使い、次のように cargo test を実行：
cargo test --test test_pop

🚨 2. Polygon::new(ring, vec![]) のリング順が反時計回りでない
geo::Polygon は基本的に 外殻リングは反時計回り（counter-clockwise） でなければなりません。
順序が逆（時計回り）だと contains() が失敗することがあります。

🔧 対処法：
let mut ring: Vec<Coord<f64>> = it.coords.iter()
    .map(|(lon, lat)| Coord { x: *lon, y: *lat })
    .collect();

let line_string = geo::LineString::from(ring.clone());
let polygon = geo::Polygon::new(line_string, vec![]);

// 検証用ログ出力
println!(">>> Constructed polygon for city: {}, ring = {:?}", it.city_id, ring);
→ これにより、座標列を出力して「明らかに正しいか」を手で検証できます。
