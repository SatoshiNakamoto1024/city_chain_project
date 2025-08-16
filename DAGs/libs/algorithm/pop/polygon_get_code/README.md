1. get_kanazawa_polygon.py
このコードは、Overpass API に対して金沢市の行政境界情報を問い合わせ、結果を GeoJSON 形式に変換して指定フォルダに出力します。
ファイルパス例：
D:\city_chain_project\PoP\poligon_get_code\get_kanazawa_polygon.py
import requests
import json
import os

# Overpass API のエンドポイント
OVERPASS_URL = "http://overpass-api.de/api/interpreter"

# 金沢市の行政境界を取得するための Overpass クエリ
# "name:ja"="金沢市" かつ "boundary"="administrative" を対象としています
QUERY = """
[out:json][timeout:25];
relation["name:ja"="金沢市"]["boundary"="administrative"];
out geom;
"""

def fetch_kanazawa_polygon():
    """
    Overpass API にクエリを送り、金沢市の行政境界データ（JSON形式）を取得する。
    取得結果から、GeoJSON形式の FeatureCollection を生成して返す。
    """
    print("Overpass API へクエリ送信中...")
    response = requests.post(OVERPASS_URL, data=QUERY)
    if response.status_code != 200:
        raise Exception("Error fetching data: HTTP {}".format(response.status_code))
    data = response.json()
    features = []
    # Overpass の結果は elements に格納される。typeがrelationのものに対して geometry 配列から座標リストを作成する
    for element in data.get("elements", []):
        if element["type"] == "relation":
            # geometry は [ { "lat": ..., "lon": ... }, ... ]
            coords = []
            for geo in element.get("geometry", []):
                # GeoJSON は [longitude, latitude] の順で指定する
                coords.append([geo["lon"], geo["lat"]])
            # GeoJSON のPolygonでは座標リストを [ [x1, y1], [x2, y2], ... ] として、外周が閉じている必要がある
            if coords and coords[0] != coords[-1]:
                coords.append(coords[0])
            feature = {
                "type": "Feature",
                "properties": {
                    "id": element["id"],
                    "name": element.get("tags", {}).get("name:ja", "金沢市")
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            }
            features.append(feature)
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    return geojson_data

def save_geojson(data, filepath):
    """
    GeoJSON データを指定されたファイルに保存する。
    """
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"GeoJSON data saved to: {filepath}")

if __name__ == "__main__":
    try:
        print("Fetching Kanazawa polygon data from Overpass API...")
        geojson_data = fetch_kanazawa_polygon()
        # 出力先ディレクトリ（例：D:\city_chain_project\PoP\poligon_data\）
        output_dir = r"D:\city_chain_project\PoP\poligon_data"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "kanazawa.geojson")
        save_geojson(geojson_data, output_path)
    except Exception as e:
        print("Error:", e)

2. README.md
以下は、D:\city_chain_project\PoP\poligon_get_code\ に配置する README.md の全文サンプルです。
# ポリゴンデータ取得プログラム

このプロジェクトは、Overpass API を利用して金沢市の行政境界ポリゴンデータを取得し、GeoJSON 形式で保存する Python スクリプトを提供します。

## ディレクトリ構成

D:
└─ city_chain_project └─ PoP ├─ poligon_data │ └─ (ここに取得した GeoJSON ファイルが保存される) └─ poligon_get_code ├─ get_kanazawa_polygon.py └─ README.md

- **poligon_data**: 取得したポリゴンデータ（GeoJSONファイル）が出力されるフォルダです。
- **poligon_get_code**: ポリゴンデータ取得用のコードおよび本README.mdが配置されるフォルダです。

## 必要な環境

- Python 3.7 以上
- 必要な Python パッケージ:
  - `requests`
  - (標準ライブラリのみでも動作可能ですが、json, os, threading などを使用します)

インストール方法（pip を利用する場合）:

```bash
pip install requests
実行手順
Overpass API の確認
このスクリプトは Overpass API を利用して金沢市の行政境界情報を取得します。インターネットに接続され、APIのエンドポイント（http://overpass-api.de/api/interpreter）がアクセス可能であることを確認してください。

出力先ディレクトリの確認
スクリプトでは出力先ディレクトリとして D:\city_chain_project\PoP\poligon_data を使用しています。必要に応じてディレクトリパスを変更してください。

スクリプトの実行
コマンドラインから以下のコマンドを実行してください：

bash
Copy
python get_kanazawa_polygon.py
結果の確認
実行後、D:\city_chain_project\PoP\poligon_data\kanazawa.geojson というファイルが作成され、金沢市の行政境界ポリゴンが GeoJSON 形式で保存されます。ファイルをテキストエディタや GIS ソフト（例：QGIS）で開いて、境界が正しく表示されることを確認してください。

注意事項
Overpass API はリクエスト数に制限があります。大量のリクエストを送信する場合、API の利用制限に達する可能性がありますので、利用時は注意してください。

金沢市の行政境界は実際には非常に複雑な形状をしているため、取得されたポリゴンは多数の座標点からなる場合があります。取得後のデータサイズに注意してください。

実運用では、より正確な行政区域データ（例えば、国土地理院やオープンデータとして提供されている GeoJSON を利用）を使用することが推奨されます。

トラブルシューティング
HTTP エラーが発生する場合

Overpass API のエンドポイントが変更されていないか、またはアクセス制限にかかっていないか確認してください。

出力ファイルが生成されない場合

実行時にエラーメッセージが表示されるか確認し、Python の例外内容をチェックしてください。

以上が本プロジェクトの概要と実行手順です。必要に応じてコードや設定を変更し、実環境に合わせた調整を行ってください。

yaml
Copy

---

## まとめ

- **get_kanazawa_polygon.py**  
  - Overpass API を用いて金沢市の行政境界データを取得し、GeoJSON ファイルとして `D:\city_chain_project\PoP\poligon_data\kanazawa.geojson` に保存するコードです。  
- **README.md**  
  - このコードの使用方法、必要環境、実行手順、および注意事項を詳細に説明したファイルです。

これらのファイルを配置すれば、実際に金沢市の詳細な行政境界データを取得し、指定フォルダに出力すること