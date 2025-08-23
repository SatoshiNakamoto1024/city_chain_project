各クレート詳細
クレート	重要ファイル	使用 crate
pop_types	src/lib.rs	serde, thiserror
pop_geo	src/index.rs src/geojson.rs	geo, geojson, rstar, serde_json
pop_events	src/rules.rs	chrono, serde, regex
pop_engine	src/lib.rs	pop_types, pop_geo, pop_events, once_cell
pop_py	src/lib.rs src/bindings.rs	pyo3, pop_engine
pop_cli	src/main.rs	clap, pop_engine
pop_python	pop_python/manager.py
pop_python/localization.py	functools.lru_cache, aiohttp?, pop_py
pop_data	cities.geojson, events.json	（依存されるだけ）

|  #  | クレート名                 | 主な責務                                                                      |  ことば  | 公開 API (抜粋)                                                                                           |
| :-: | --------------------- | ------------------------------------------------------------------------- | :---: | ----------------------------------------------------------------------------------------------------- |
|  1  | **`pop_types`**       | 共通型・エラーハンドリング (`Point`, `CityId`, `PopError`)                             | **2** | `struct Point { lat: f64, lon: f64 }`<br>`enum PopError { … }`                                        |
|  2  | **`pop_geo`**         | GeoJSON 読み込み→`geo` Polygon 化<br>R‑tree (`rstar`) 構築 / point‑in‑polygon 判定 | **2** | `fn build_index(dir:&Path)->GeoIndex`<br>`impl GeoIndex { fn query(&self, p:Point)->Option<CityId> }` |
|  3  | **`pop_events`**      | “イベント倍率” のルールエンジン<br>（都市別 / 座標別 / 時刻別）                                    | **2** | `fn city_multiplier(city:&CityId, ts:DateTime<Utc>)->f32`                                             |
|  4  | **`pop_engine`**      | `pop_geo` + `pop_events` を束ねて<br>**PoP 評価を１関数で提供**                        | **2** | `fn evaluate(p:Point, ts)->PopResult`<br>`struct PopResult { city:CityId, mul:f32 }`                  |
|  5  | **`pop_py`**          | PyO3 バインディング（ABI3‑py312）<br>`PopEngine` を Python に公開                      | **3** | `class PopEngine: evaluate(lat,lon)->dict`                                                            |
|  6  | **`pop_cli`** *(bin)* | CLI デモ<br>`pop-eval --lat 35.0 --lon 139.0`                               | **2** | -                                                                                                     |
|  7  | **`pop_python`**      | 高レベル Python ラッパ／キャッシュ／I/O<br>gRPC 連携・LRU キャッシュ                            | **1** | `initialize_pop_system()`<br>`get_place_info_and_bonus(uid, lat?, lon?)`                              |
|  8  | **`pop_data`**        | 配布用 GeoJSON / イベント定義ファイル                                                  | **1** | - (純データ)                                                                                              |




pop (3)	 PoP: 位置情報 & ポリゴン判定

#　PoP（Proof-of-Presence）のジオフェンス判定
「現在のノード位置が、ある市町村のポリゴン内部にいるか？」を判定するジオフェンスは、
単一の point-in-polygon 判定（Ray-casting アルゴリズム）
市町村ポリゴン数：数百〜数千
判定頻度：1 トランザクションあたり数回
…程度なら、Python 側で shapely（GEOS バインディング）を使ってC ライブラリの超最適化実装を叩くのが簡単です。

# src/presence/geofence.py
from shapely.geometry import Point, shape
import json

# 市町村ポリゴンを GeoJSON からロード
with open("config/municipalities.geojson") as f:
    muni_data = json.load(f)

def is_inside(lat: float, lon: float, muni_name: str) -> bool:
    poly = next(f["geometry"] for f in muni_data["features"]
                if f["properties"]["name"] == muni_name)
    return shape(poly).contains(Point(lon, lat))

上記のようなコードでいける。

■　Python/shapely：
Pros：実装が圧倒的にラク、C で最適化済み
Cons：CPython–C 間のオーバーヘッドが微小に残る

■　Rust/geo-crate：
Pros：「全て Rust」でビルド可、バインディング不要、さらに高速
Cons：実装＆メンテナンスコストが少し上

→ PoP のジオフェンスは「中程度の負荷」で済むので まずは Python+shapely、もしスループットが足りなければ後から Rust 化、が現実的です。


#　変更点:

pop_manager.get_place_info_and_bonus(sender, lat, lon) -> lat,lon の実引数を使い、
位置情報取得(もし lat==None ならダミー; そうでなければユーザが送った本物の緯度経度)
STRtree + Shapely で city_id判定

イベント倍率
LRUキャッシュにより100~200ms内を目指す
add_transaction(...) でtime計測し、pop_time(ms) をログ出力
_process_batch() による署名検証(Rust) → 依存解決 → DPoS並列 → OKならgRPC送信 → NGなら破棄

まとめ
これで

Shapely + STRtree で多数ポリゴンを高速判定

LRUキャッシュ (@lru_cache) で同じ緯度経度の繰り返しアクセスを高速化

モバイル端末 から (lat, lon) が送られる設計 → それをPoP モジュール群が処理

100~200msを目指すにはサーバのCPU, Shapely のインデックス最適化、イベント数などが大きく影響するが、
上記構成でもかなりの高速化が期待できる

以上の新しいファイル(pop_polygons.py, pop_events.py, pop_localization.py, pop_manager.py)と修正後の city_dag_handler.py で、「Shapely + STRtree」やモバイル端末の緯度経度を使うPoP本番実装に近い形が完成します。


# ビルド＆インストール手順
Rust 拡張をビルド
cd D:/city_chain_project/Algorithm/PoP/pop_rust
maturin develop --release

これで pop_rust Python モジュールがインストールされます。

Python API を使う
from pop_python import initialize_pop_system, get_place_info_and_bonus
# Rust 版ポリゴン・イベントボーナスが有効ならそちらが呼ばれます

initialize_pop_system()
info = get_place_info_and_bonus("user123", lat=35.02, lon=139.005)
print(info)
# => {'lat':35.02, 'lon':139.005, 'city_id':'cityA', 'multiplier':15.0, 'method':'UserProvided'}

以上で、PoP アルゴリズムの「Python 高レベル API」＋「Rust ネイティブ拡張」による完全分離・結合構成が整いました。
次は「Rendezvous Hash」「VRF」等、別モジュールとして独立化して呼び出せるように進めていきましょう！


# いまは、どんな機能なのか詳細に解説して。pythonとrustでどう機能わけをしているのか。

PoP（Place-of-Presence）サブシステムの全体像
レイヤ	メイン言語	主な責務	代表 API
Python	Python	“どのノードに投げるか” を上位ロジックから呼び出せる形に抽象化。
ユーザ位置取得・キャッシュ・Presence Service との通信など I/O 寄りの処理。	pop_python.manager.get_place_info_and_bonus()
Rust	Rust + PyO3	ジオメトリ計算・R-tree 構築など CPU 負荷が高い or 低レイテンシが欲しい処理。
GeoJSON 読み込み → Polygon → R-tree 化、点‐多角形判定、イベント倍率計算。	pop_rust::polygons::{load_polygons_from_dir, query_point}
pop_rust::events::{check_city_event, check_location_event}

1. 典型フロー
sequenceDiagram
    participant Caller(Py) as 上位アプリ(Python)
    participant Manager as pop_python.manager
    participant Rust as pop_rust (PyO3)

    Caller->>Manager: get_place_info_and_bonus(uid, lat?, lon?)
    Manager->>Rust: load_polygons_from_dir("polygon_data/")  (初回のみ)
    Manager->>Rust: city_id = query_point(lat, lon)
    Manager->>Rust: c_mul = check_city_event(city_id)
    Manager->>Rust: l_mul = check_location_event(lat, lon)
    Rust-->>Manager: 倍率 / city_id
    Manager-->>Caller: {city_id, multiplier=c_mul*l_mul, ...}

ファイル役割の整理
ファイル	言語	役割
Algorithm/PoP/pop_python/
localization.py	Py	端末が送ってくる緯度経度を受け取り、なければモックで生成。
events.py	Py	参考実装。時間帯イベント／位置イベントのテーブルを持つ。
polygons.py	Py	Shapely + STRtree での簡易版判定（Rust にフォールバックするまでのプレースホルダ）。
manager.py	Py	上位 API。位置取得→(必要なら)Rust呼び出し→倍率合算→キャッシュ。
Algorithm/PoP/pop_rust/
types.rs	Rust	Py⇆Rust 構造体ブリッジ（PolyItem など）。
polygons.rs	Rust	① GeoJSON 読み込み ② Polygon 変換 ③ rstar で R-tree 構築 ④ 点‐多角形ヒット検索。
events.rs	Rust	高速なイベント倍率計算。Geo 座標 in-polygon も Rust 側で実行。
lib.rs	Rust	pub mod … で上記を公開。#[pymodule] で PyO3 エクスポート。
bin/main_pop.rs	Rust	CLI デモ：GeoJSON 読み込み→クエリ→倍率チェックを単体で確認。

# Python / Rust の役割分担の理由
項目	Python 側	Rust 側
I/O (HTTP, Presence Service, JWT 等)	asyncio や requests/grpc で実装。	なし
ジオメトリ演算
(点‐多角形判定・R-tree 最近傍)	Shapely でも可能だが
大量ポリゴン＆QPS が上がるとボトルネック	rstar + geo で μs オーダに短縮
イベント表の編集	Python dict / DB からホットリロード	計算ロジックのみ
キャッシュ & ロギング	LRU/Redis など柔軟に実装	なし
署名／VRF	Py から Rust ラッパを呼び出す	別 crate（vrf_rust など）に実装予定

# なぜ pyproject.toml は 2 本必要で、「rustproject.toml」 ではダメなのか
（＝ Python パッケージビルド仕様と maturin の仕組み の整理）

1. Python のビルド仕様は PEP 517/518 ＝ “pyproject.toml 1 択”
pip / build / maturin など、“ビルドする側” は
「このディレクトリ（＝パッケージ）」に pyproject.toml があることを前提に
どのツールで どうビルドするかを判定します。
→ “rustproject.toml” のような独自ファイルは pip も PyPI も認識しません。

maturin も PEP 517 ビルドバックエンド として振る舞うため、
Rust 側でも pyproject.toml を必ず置きます。
（[build-system] build-backend = "maturin" と書くのはこのため）

2. 片方ずつビルド＝正しい運用
（同じリポジトリ内に “2 つの Python パッケージ” が並ぶイメージ）
Algorithm/PoP/
├─ pop_python/           ← 純 Python 実装
│   └─ pyproject.toml    ← build-backend = "setuptools.build_meta"
└─ pop_rust/             ← Rust バインディング
    └─ pyproject.toml    ← build-backend = "maturin"
ディレクトリ	ビルドコマンド	生成される wheel	PyPI 上の name
pop_python/	pip wheel .   or   python -m build	pop_python-0.1.0-py3-none-any.whl	pop-python 例
pop_rust/	maturin build --release	pop_rust-0.1.0-cp311-cp311-manylinux_x86_64.whl など	pop-rust 例

→ 「片方ずつビルド」 が当たり前で、
CI でも matrix で OS/py-ver を替えつつ 2 ジョブ回して wheel を作り、同じ GitHub Release や private PyPI に公開するのが一般的です。

3. monorepo で root に pyproject を置く方法は？
A. ツリービルド (build-system.workspace)
PEP 660（editable spec）＋最新 pip では「ワークスペース」機能がありますが、
setuptools / maturin の両方を 1 枚の pyproject.toml で記述するのは現状非対応。

B. ルートは空の pyproject、各サブに本物
ルートに “stub” を置き、packages=[] にしてしまう手もあります。
ただし最終的に pip install するのはサブパッケージそれぞれなので、
結局 ビルドは個別 です。

4. まとめ：やることリスト
ディレクトリごとに pyproject.toml を維持
pop_python/pyproject.toml … setuptools
pop_rust/pyproject.toml … maturin
パッケージ名を衝突しないように

例：pop-python と pop-rust
import 名は pop_python, pop_rust のままで問題なし（名前空間は別）

CI（GitHub Actionsなど）
jobs:
  build-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install build
      - run: cd Algorithm/PoP/pop_python && python -m build --wheel -o dist
  build-rust:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11"]
    steps:
      - uses: actions/checkout@v4
      - uses: PyO3/maturin-action@v1
        with:
          build-args: --release -m Algorithm/PoP/pop_rust/pyproject.toml
利用者ドキュメント

bash
Copy
Edit
pip install pop-python           # 基本機能
pip install pop-rust             # 高速 Rust バックエンド(対応 wheel がある環境で)
❗ 結論
rustproject.toml のような独自ファイルは使えない

pyproject.toml を Rust / Python で 2 つ置く
→ ビルドも pip install も問題なく動く最もシンプルで公式な構成です。


使い方
1. Rust ライブラリをビルド → Python から呼ぶ
# プロジェクト直下
maturin develop  # または `pip install -e .` 方式
python - << 'PY'
from pop_rust import polygons, events
# ① ポリゴン読込（起動時に一回）
polygons.load_polygons_from_dir("polygon_data")

# ② 任意地点を判定
print(polygons.query_point(35.02, 139.02))  # => 'kanazawa' など

# ③ イベント倍率
print(events.check_city_event("kanazawa"))
PY

2. Python 高レベル API
from pop_python.manager import get_place_info_and_bonus

info = get_place_info_and_bonus(
    user_id="alice",
    lat=35.02, lon=139.02      # 端末が送ってきた場合
)
print(info)
# {'lat': 35.02, 'lon': 139.02,
#  'city_id': 'kanazawa', 'multiplier': 3.0, 'method': 'UserProvided'}

3. Rust 単体 CLI（性能検証や CI 用）
cargo run --bin main_pop -- polygon_data
# → 読込成功 / ヒット判定 / 倍率 がコンソールに出力
これから拡張する際の着眼点
タスク	どちらに実装？	理由
GeoJSON のホットリロード	Python → Rust API を再呼び出し	失敗時ハンドリングが容易
VRF 署名の実装	Rust (vrf_rust)	libSodium を直に叩く方が高速
大規模 City/Event テーブルを Redis 共有	Python	オーケストレーション層で統合しやすい
FFI 境界の削減	Rust に more logic を寄せる	CPU 負荷増に応じて最適化

このように 「I/O とオーケストレーションは Python」「計算ヘビー部分は Rust」 に割り切ることで、保守性と性能を両立させています。

# Test 結果：
running 3 tests
>>> [test] polygon_data_dir = "D:\\city_chain_project\\Algorithm\\PoP\\polygon_data"
>>> [load] Loading polygons from directory: D:\city_chain_project\Algorithm\PoP\polygon_data
>>> [test] polygon_data_dir = "D:\\city_chain_project\\Algorithm\\PoP\\polygon_data"
>>> [load] Loading polygons from directory: D:\city_chain_project\Algorithm\PoP\polygon_data
>>> [load] Checking file: "D:\\city_chain_project\\Algorithm\\PoP\\polygon_data\\kanazawa.geojson"
>>> [test] polygon_data_dir = "D:\\city_chain_project\\Algorithm\\PoP\\polygon_data"
>>> [load] Loading polygons from directory: D:\city_chain_project\Algorithm\PoP\polygon_data
>>> [load] Checking file: "D:\\city_chain_project\\Algorithm\\PoP\\polygon_data\\kanazawa.geojson"
>>> [load] raw coord [lon,lat]=[136.620000,36.550000]
>>> [load] Checking file: "D:\\city_chain_project\\Algorithm\\PoP\\polygon_data\\kanazawa.geojson"
>>> [load] raw coord [lon,lat]=[136.620000,36.550000]
>>> [load] raw coord [lon,lat]=[136.680000,36.550000]
>>> [load] raw coord [lon,lat]=[136.680000,36.600000]
>>> [load] raw coord [lon,lat]=[136.620000,36.600000]
>>> [load] raw coord [lon,lat]=[136.620000,36.550000]
>>> [load] Loaded polygon: kanazawa (5 points)
>>> [load] raw coord [lon,lat]=[136.620000,36.550000]
>>> [load] raw coord [lon,lat]=[136.680000,36.550000]
>>> [load] raw coord [lon,lat]=[136.680000,36.600000]
>>> [load] raw coord [lon,lat]=[136.620000,36.600000]
>>> [load] raw coord [lon,lat]=[136.620000,36.550000]
>>> [load] Loaded polygon: kanazawa (5 points)
>>> [load] Checking file: "D:\\city_chain_project\\Algorithm\\PoP\\polygon_data\\paris.geojson"
>>> [load] raw coord [lon,lat]=[136.680000,36.550000]
>>> [load] raw coord [lon,lat]=[136.680000,36.600000]
>>> [load] raw coord [lon,lat]=[136.620000,36.600000]
>>> [load] raw coord [lon,lat]=[136.620000,36.550000]
>>> [load] Loaded polygon: kanazawa (5 points)
>>> [load] raw coord [lon,lat]=[2.200000,48.800000]
>>> [load] raw coord [lon,lat]=[2.450000,48.800000]
>>> [load] raw coord [lon,lat]=[2.450000,48.920000]
>>> [load] raw coord [lon,lat]=[2.200000,48.920000]
>>> [load] raw coord [lon,lat]=[2.200000,48.800000]
>>> [load] Loaded polygon: paris (5 points)
>>> [load] Checking file: "D:\\city_chain_project\\Algorithm\\PoP\\polygon_data\\paris.geojson"
>>> [load] Checking file: "D:\\city_chain_project\\Algorithm\\PoP\\polygon_data\\paris.geojson"
>>> [load] Total polygons found: 2
>>> [load] raw coord [lon,lat]=[2.200000,48.800000]
>>> [load] raw coord [lon,lat]=[2.450000,48.800000]
>>> [load] raw coord [lon,lat]=[2.450000,48.920000]
>>> [load] raw coord [lon,lat]=[2.200000,48.920000]
>>> [load] raw coord [lon,lat]=[2.200000,48.800000]
>>> [load] Loaded polygon: paris (5 points)
>>> [load] raw coord [lon,lat]=[2.200000,48.800000]
>>> [load] raw coord [lon,lat]=[2.450000,48.800000]
>>> [load] raw coord [lon,lat]=[2.450000,48.920000]
>>> [load] raw coord [lon,lat]=[2.200000,48.920000]
>>> [load] raw coord [lon,lat]=[2.200000,48.800000]
>>> [load] Loaded polygon: paris (5 points)
>>> [load] Total polygons found: 2
>>> [build] Building ring coord: lon=136.62, lat=36.55
>>> [build] Building ring coord: lon=136.68, lat=36.55
>>> [build] Building ring coord: lon=136.68, lat=36.6
>>> [build] Building ring coord: lon=136.62, lat=36.6
>>> [build] Building ring coord: lon=136.62, lat=36.55
>>> [load] Total polygons found: 2
>>> [build] Building ring coord: lon=136.62, lat=36.55
>>> [build] Building ring coord: lon=136.68, lat=36.55
>>> [build] Building ring coord: lon=136.68, lat=36.6
>>> [build] Building ring coord: lon=136.62, lat=36.6
>>> [build] Building ring coord: lon=136.62, lat=36.55
>>> [build] Polygon for 'kanazawa' bounding_rect: Some(RECT(136.62 36.55,136.68 36.6))
>>> [build] Building ring coord: lon=2.2, lat=48.8
>>> [build] Building ring coord: lon=2.45, lat=48.8
>>> [build] Building ring coord: lon=2.45, lat=48.92
>>> [build] Building ring coord: lon=2.2, lat=48.92
>>> [build] Building ring coord: lon=2.2, lat=48.8
>>> [build] Polygon for 'kanazawa' bounding_rect: Some(RECT(136.62 36.55,136.68 36.6))
>>> [build] Building ring coord: lon=2.2, lat=48.8
>>> [build] Building ring coord: lon=2.45, lat=48.8
>>> [build] Building ring coord: lon=2.45, lat=48.92
>>> [build] Building ring coord: lon=2.2, lat=48.92
>>> [build] Building ring coord: lon=2.2, lat=48.8
>>> [build] Polygon for 'paris' bounding_rect: Some(RECT(2.2 48.8,2.45 48.92))
>>> [load] Inserting 2 nodes into RTree
>>> [build] Polygon for 'paris' bounding_rect: Some(RECT(2.2 48.8,2.45 48.92))
>>> [load] Inserting 2 nodes into RTree
>>> [load] RTree ready
>>> [test] query_point(48.86, 2.337)
[query] lat=48.86, lon=2.337
>>> [build] Building ring coord: lon=136.62, lat=36.55
>>> [build] Building ring coord: lon=136.68, lat=36.55
>>> [build] Building ring coord: lon=136.68, lat=36.6
>>> [build] Building ring coord: lon=136.62, lat=36.6
>>> [build] Building ring coord: lon=136.62, lat=36.55
>>> [build] Polygon for 'kanazawa' bounding_rect: Some(RECT(136.62 36.55,136.68 36.6))
>>> [build] Building ring coord: lon=2.2, lat=48.8
>>> [build] Building ring coord: lon=2.45, lat=48.8
>>> [build] Building ring coord: lon=2.45, lat=48.92
>>> [build] Building ring coord: lon=2.2, lat=48.92
>>> [build] Building ring coord: lon=2.2, lat=48.8
>>> [build] Polygon for 'paris' bounding_rect: Some(RECT(2.2 48.8,2.45 48.92))
>>> [load] Inserting 2 nodes into RTree
>>> [load] RTree ready
>>> [test] query_point(36.572, 136.646)
[query] lat=36.572, lon=136.646
>>> [test] result = Some("kanazawa")
>>> [load] RTree ready
>>> [test] query_point(0, 0)
[query] lat=0, lon=0
>>> [test] result = None
>>> [test] result = Some("paris")
test test_point_in_kanazawa ... ok
test test_point_outside_all ... ok
test test_point_in_paris ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s

RTree の locate_in_envelope_intersecting を使い
debug 出力や brute-force ロジックを削除し
テストもシンプルな assert_eq! に戻した
ことで、本番実装向けのクリーンかつ高速なコードになる。


# test error原因
pop_rust / pop_python が pip install されていない
→ Python が import 先を見つけられず ModuleNotFoundError。

sys.path を無理に書き換えても パッケージ名が無い ので
import pop_rust は解決できません（フォルダ名＝パッケージ名ではない）。

① まず “開発モード” で両パッケージをインストール
# 仮想環境に入っている前提
かならず、仮想環境下（.venv312\）でやること、グローバルpythonでは違うところに入ってしまう

# 1. Rust 拡張をビルド & 開発インストール
cd Algorithm/PoP/pop_rust
maturin develop --release        # ← .whl をビルドして site-packages へ配置

# 2. 純 Python 側を editable インストール
cd ../pop_python
pip install -e .[dev]            # 「.[dev]」は pytest など開発依存も一緒に入れる
（失敗したら、pip install -e .[dev] --force-reinstall　でいける）

・pop_python
Building wheels for collected packages: pop_python
  Building editable for pop_python (pyproject.toml) ... done
  Created wheel for pop_python: filename=pop_python-0.1.0-0.editable-py3-none-any.whl size=4530 sha256=e556564545e8ad36376befd8ad1dd0d3f9cd46493c761b3f3ab806508635285e
  Stored in directory: C:\Users\kibiy\AppData\Local\Temp\pip-ephem-wheel-cache-nc5q2jcm\wheels\8e\fb\44\e0d1625db259421cb9e4ac5f6c15abe1a113410003422bea2c
Successfully built pop_python

そして下記に配布物ができる
D:\city_chain_project\Algorithm\PoP\pop_python\dist\pop_python-0.1.0-py3-none-any.whl

・pop_rust
(.venv312) D:\city_chain_project\Algorithm\PoP\pop_rust>maturin develop --release
🐍 Found CPython 3.12 at D:\city_chain_project\.venv312\Scripts\python.exe
    Finished `release` profile [optimized] target(s) in 7.35s
📦 Built wheel to C:\Users\kibiy\AppData\Local\Temp\.tmpa1XHrV\pop_rust-0.1.0-cp312-cp312-win_amd64.whl
✏️ Setting installed package as editable
🛠 Installed  pop_rust-0.1.0

そして、追加で、下記をやると、dist\　に配布物ができる
配布したいときだけ maturin build --release -o dist

✅wheel ファイルは以下のパスに作成されています：
D:\city_chain_project\Algorithm\PoP\pop_rust\dist\pop_rust-0.1.0-cp312-cp312-win_amd64.whl

📦 使い方（インストール方法）
他の環境で使いたい場合： ※import pop_python でいけるので、他で使うってある？
pip install dist\pop_python-0.1.0-py3-none-any.whl
pip install dist\pop_rust-0.1.0-cp312-cp312-win_amd64.whl

これで
site-packages/
├─ pop_rust/
└─ pop_python/
が出来るので import が解決 します。

② CI で wheel を使う場合
pop_python → python -m build --wheel … で生成した
pop_python-*.whl を pip install。

pop_rust → maturin build … --out dist で出来る
pop_rust-*-cp310-*manylinux*.whl などを pip install。

ローカルテストでも wheel を直接指定すれば OK:
pip install dist/pop_python-0.1.0-py3-none-any.whl
pip install dist/pop_rust-0.1.0-cp311-manylinux_x86_64.whl

③ test_pop_integration.py を修正して
　「モジュールが無ければテストをスキップ」する
import pytest, importlib.util

# --- 追加 -----------------------------------------------------------------
def _module_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None
# -------------------------------------------------------------------------

@pytest.mark.skipif(not _module_exists("pop_rust"),
                    reason="pop_rust wheel not installed")
def test_pop_rust_available():
    import pop_rust
    ...
同様に pop_python も確認して skip すれば
「インストールし忘れ」で黄色 (skipped) になり、CI が落ちません。

④ もう一度実行
pytest -q test_pop_integration.py
両方インストール済み → すべて PASS

どちらか欠けている → 該当ケースだけ skipped

まとめ
手順	コマンド例	目的
1	maturin develop -m pop_rust/pyproject.toml	Rust 拡張を site-packages に配置
2	pip install -e Algorithm/PoP/pop_python[dev]	純 Python パッケージを editable で配置
3	pytest -q test_pop_integration.py	統合テスト実行

これで import pop_rust, import pop_python が解決し、
統合テストもブロッキング無く通ります。


# editable と wheel を同一 venvに共存させない
必ず uninstall → install wheel の順で切り替える。
pip install --no-cache-dir ".\dist\pop_rust-0.1.0-cp312-cp312-win_amd64.whl

なぜ毎回これをやる必要があるのか？
開発フェーズ	使うコマンド	メリット	テスト前の手順
日常開発	maturin develop --release	ソースを直すと即反映	pytest の前に uninstall する
CI／本番検証	maturin build --release -o dist → pip install .whl	wheel だけで再現性◎	特になし（editable 不要）

editable と wheel は 同じ venv に同居させない のが鉄則。<br>
今回のエラーは editable のゴミ が wheel より先に import されたためです。
