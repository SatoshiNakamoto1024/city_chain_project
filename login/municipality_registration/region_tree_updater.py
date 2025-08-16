# municipality_registration/region_tree_updater.py

import json
import logging
from pathlib import Path

from municipality_registration.config import REGION_JSON

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def load_region_tree() -> dict:
    """
    region_tree.json を読み込む。
    存在しない場合は空オブジェクト {} を作成します。
    """
    path = Path(REGION_JSON)
    if not path.exists():
        logger.warning(f"{REGION_JSON} が存在しないため新規作成します。")
        path.write_text("{}", encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))

def save_region_tree(data: dict):
    """
    region_tree.json に JSON データを書き込みます。
    """
    path = Path(REGION_JSON)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    logger.info("region_tree.json を保存しました。")

def update_region_tree(
    continent: str,
    country_code: str,
    country_name: str,
    pref_code: str,
    pref_name: str,
    city_name: str
) -> None:
    """
    region_tree.json に新しい市町村を追加します。
    大陸／国／都道府県がまだなければ自動で階層を作成します。
    """
    reg = load_region_tree()
    cont = reg.setdefault(continent, {"countries": []})

    # ── 国を追加 or 取得 ─────────────────────
    country = next(
        (c for c in cont["countries"] if c["code"] == country_code),
        None
    )
    if not country:
        country = {
            "code": country_code,
            "name": country_name,
            "prefectures": []
        }
        cont["countries"].append(country)

    # ── 都道府県を追加 or 取得 ────────────────
    pref = next(
        (p for p in country["prefectures"] if p["code"] == pref_code),
        None
    )
    if not pref:
        pref = {
            "code": pref_code,
            "name": pref_name,
            "cities": []
        }
        country["prefectures"].append(pref)

    # ── 市町村を追加（重複チェック） ───────────
    if city_name not in pref["cities"]:
        pref["cities"].append(city_name)
        logger.info(f"{continent}/{country_name}/{pref_name}/{city_name} を追加しました。")
    else:
        logger.info(f"{city_name} はすでに存在します。")

    # ── 保存 ─────────────────────────────────
    save_region_tree(reg)
