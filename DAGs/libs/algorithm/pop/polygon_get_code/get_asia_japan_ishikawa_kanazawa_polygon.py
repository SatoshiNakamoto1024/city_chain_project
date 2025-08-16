import requests
import json
import os

try:
    import osmtogeojson
    print(hasattr(osmtogeojson, 'convert'))  # True が出ればOK
except ImportError:
    osmtogeojson = None

# Overpass API のエンドポイント（HTTPS、lz4 ミラーを利用）
OVERPASS_URL = "https://lz4.overpass-api.de/api/interpreter"

# 金沢市の関係ID (4800041) を使って、リレーションとそのメンバー（ウェイ、ノード）を再帰的に取得するクエリ
QUERY = """
[out:json][timeout:25];
relation(4800041);
(._;>;);
out meta geom;
"""

def fetch_kanazawa_polygon():
    headers = {
        "User-Agent": "MyOverpassClient/1.0 (next_teal_organization@gmail.com)"
    }
    response = requests.post(OVERPASS_URL, data={'data': QUERY}, headers=headers)
    if response.status_code != 200:
        raise Exception("Error fetching data: HTTP {}".format(response.status_code))
    
    osm_data = response.json()
    
    # チェック：relationタイプの要素にジオメトリが含まれているか
    has_geom = False
    for element in osm_data.get("elements", []):
        if element["type"] == "relation" and "geometry" in element and element["geometry"]:
            has_geom = True
            break

    if not has_geom:
        print("Warning: relation 4800041 has no geometry data using query; attempting conversion with osmtogeojson...")
        if osmtogeojson is not None and hasattr(osmtogeojson, 'convert'):
            geojson_data = osmtogeojson.convert(osm_data)
            return geojson_data
        else:
            raise Exception("No geometry data returned and osmtogeojson.convert is not available.")
    
    # geometry がある場合、そのデータを元に GeoJSON を組み立てる
    features = []
    for element in osm_data.get("elements", []):
        if element["type"] == "relation" and "geometry" in element and element["geometry"]:
            coords = []
            for geo in element["geometry"]:
                coords.append([geo["lon"], geo["lat"]])
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
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"GeoJSON data saved to: {filepath}")

if __name__ == "__main__":
    try:
        print("Fetching Kanazawa polygon data from Overpass API...")
        geojson_data = fetch_kanazawa_polygon()
        output_dir = r"D:\city_chain_project\PoP\poligon_data"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "kanazawa.geojson")
        save_geojson(geojson_data, output_path)
    except Exception as e:
        print("Error:", e)
