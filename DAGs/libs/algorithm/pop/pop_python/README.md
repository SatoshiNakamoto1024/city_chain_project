D:\city_chain_project\Algorithm\PoP\
├── pop_python\
│   ├── __init__.py
│   ├── events.py
│   ├── localization.py
│   ├── manager.py
│   └── polygons.py
    └── geolocation\
└── pop_rust\
    ├── Cargo.toml
    └── src\
        ├── lib.rs
        ├── types.rs
        ├── polygons.rs
        └── events.rs

# 拡張を正しくビルド & インストール
maturin develop --release

あなたはもう Python から直接
import pop_rust
pop_rust.load_polygons_from_dir(...)
が呼べる状態になっています。

そのまま python app_pop.py （同じ .venv312 をアクティベートしたまま）を実行すれば、先ほど修正した __init__.py の hasattr(pop_rust, ...) 部分を通って、Rust 側の高速ルーチンが動作します。

もし別の環境で使いたい場合は、この wheel を保存しておいて…
pip install path/to/pop_rust-0.1.0-cp314-cp314-win_amd64.whl
のようにインストールすれば OK ですが、普段の開発では maturin develop だけで十分です。


# PYTHONPATH を通してテストを実行する
インストールせずにテストだけ通したいなら、カレントディレクトリをパッケージの親（Algorithm\PoP）にしてからテストを叩く方法です:
cd D:\city_chain_project\Algorithm\PoP
pytest -v pop_python/test_pop.py
こうすれば D:\city_chain_project\Algorithm\PoP が先頭に入り、import pop_python.manager が正しく解決されます。


🔍 各機能の詳細
manager.py（中核ロジック）
initialize_pop_system()：ポリゴンファイルをすべて読み込む初期化処理
get_place_info_and_bonus(user_id, lat=None, lon=None)：
lat, lon があればそれを使い、なければランダムに選ぶ
その地点がどの市町村に属するかを判定
該当地点や都市にイベントボーナスがあるか確認
PlaceInfo を返す（位置、倍率、方法）

localization.py（位置情報の取得）
入力がなければ、すでにロード済みのポリゴンからランダムに1つ選び、その中からランダムな座標をサンプリング
使われるケース：
テストや、位置情報が取得できない端末からのアクセス
シミュレーションモードなど

polygons.py（市町村ポリゴンの管理）
load_city_polygons()：
polygon_data/ にある全 .geojson ファイルを動的に読み込み
各ファイルからポリゴンと市町村IDを抽出
find_city_by_location(lat, lon)：
与えられた座標がどの市町村ポリゴンに含まれるかを返す

events.py（ボーナスイベント倍率）
check_city_event(city_id)：
特定の市町村に紐づくキャンペーン倍率（例: イベント開催中なら2倍）
check_location_event(lat, lon)：
緯度経度での局所的イベント（例: 広場・観光地など）

test_pop.py（動作確認用テスト）
位置情報の判定と倍率計算が正しく動作しているかを確認するための pytest テストコード
✅ 戻り値のサンプル
{
    "lat": 36.30351,
    "lon": 136.49822,
    "city_id": "kaga",
    "multiplier": 1.5,           # 都市倍率1.0 × ロケーション倍率1.5
    "method": "UserProvided"     # もしくは MockRandomCity:kaga
}
🧪 使用方法（Python側から呼び出す）
1. 初期化（1回だけ）
from pop_python.manager import initialize_pop_system
initialize_pop_system()

2. 場所とボーナスを取得（ユーザー指定）
from pop_python.manager import get_place_info_and_bonus

info = get_place_info_and_bonus("user1", lat=36.3, lon=136.5)
print(info)
# → {"lat": ..., "lon": ..., "city_id": ..., "multiplier": ..., "method": "UserProvided"}

3. ランダム取得（シミュレーションなど）
info = get_place_info_and_bonus("user2")
print(info)
# → {"lat": ..., "lon": ..., "city_id": ..., "multiplier": ..., "method": "MockRandomCity:xxx"}

🌐 応用例
この PoP システムは、以下のような場面で利用可能です：
シーン	使用目的
愛貨送信時	送信者の場所認証 + ボーナス倍率
観光地や地域イベント連携	特定エリアに居る人に限定愛貨を発行
DPoS代表者判定	市町村内に物理的にいるか確認
市町村外部者制限	市外ユーザーからのアクセスを制限する

🚀 次のステップ案
✅ polygon_data/ を充実させて、全国対応に
✅ check_city_event をDynamoDBなどと接続して動的イベント管理に拡張
✅ get_mobile_location をGPSやWiFi位置情報に対応
✅ Rust版とのPoP連携と統一インターフェース構築（Rust側 PoPも既に設計中）


# これを実装：geolocationに
✅ get_mobile_location をGPSやWiFi位置情報に対応
これでできること
シナリオ	送る JSON	method 返却値
GPS だけ	{"user_id":"u", "lat":35, "lon":139}	"GPS"
Wi-Fi だけ	{"user_id":"u", "wifi_data":[{"mac":"00:11","rssi":-50}]}	"WiFi"
どちらも無い	{"user_id":"u"}	"MockRandomCity:<id>"

これら 3 ファイルを差し替え後、uvicorn pop_python.app_pop:app --reload でサーバーを立ち上げ、
エンドポイント /pop へ上記 JSON を POST すれば PoP 判定が行えます。
