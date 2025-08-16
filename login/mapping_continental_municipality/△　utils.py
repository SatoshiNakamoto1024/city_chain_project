# mapping_continental_municipality/utils.py
import json
from pathlib import Path
REGION_FILE = Path(__file__).with_name("region.json")
_DATA = json.loads(REGION_FILE.read_text(encoding="utf-8"))

def continents():                           # ["Asia", ...]
    return list(_DATA.keys())

def countries(continent: str):             # → [{"code":"JP","name":"Japan"}, ...]
    return [
        {"code": c["code"], "name": c["name"]}
        for c in _DATA.get(continent, {}).get("countries", [])
    ]

def prefectures(continent: str, country: str):  # → [{"code":"18","name":"Ishikawa"}, ...]
    for c in _DATA.get(continent, {}).get("countries", []):
        if c["code"] == country:
            return [
                {"code": p["code"], "name": p["name"]}
                for p in c.get("prefectures", [])
            ]
    return []

def cities(continent: str, country: str, pref: str) -> list[str]:
    for c in _DATA.get(continent, {}).get("countries", []):
        if c["code"] == country:
            for p in c.get("prefectures", []):
                if p["code"] == pref:
                    return p.get("cities", [])
    return []

def is_valid(cont: str, country: str, pref: str, city: str) -> bool:
    return city in cities(cont, country, pref)
