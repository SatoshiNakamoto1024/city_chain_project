# mapping_continental_municipality/services.py
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
from boto3.dynamodb.conditions import Key
from mapping_continental_municipality.config import USER_LOCATION_TABLE, AWS_REGION

# DynamoDB の resource を生成
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(USER_LOCATION_TABLE)


def set_user_location_mapping(uuid: str,
                              continent: str,
                              country: str,
                              prefecture: str,
                              municipality: str) -> None:
    """
    ユーザー(UUID) に対して“大陸→国→都道府県→市町村”を紐づけて、
    UserLocationMapping テーブルに書き込む。

    PK (Partition Key) : continent
    SK (Sort Key)      : "{country}#{prefecture}#{municipality}#{uuid}"

    例:
        set_user_location_mapping(
            uuid="user-1a2b3c4d",
            continent="Asia",
            country="JP",
            prefecture="13",
            municipality="Chiyoda"
        )
    """
    # ソートキー (country#prefecture#municipality#uuid) を作成
    location_uuid = f"{country}#{prefecture}#{municipality}#{uuid}"

    item = {
        "continent":      continent,
        "location_uuid":  location_uuid,
        "country":        country,
        "prefecture":     prefecture,
        "municipality":   municipality,
        "uuid":           uuid,
    }
    table.put_item(Item=item)


def get_users_by_location(continent: str,
                          country: str = None,
                          prefecture: str = None,
                          municipality: str = None) -> list[dict]:
    """
    指定された“大陸→国→都道府県→市町村”に属するユーザー一覧を取得する。

    - continent のみ指定 => 当該大陸に属する全ユーザー
    - continent + country => 当該大陸・国に属する全ユーザー
    - continent + country + prefecture => 当該大陸・国・県に属する全ユーザー
    - 上記 + municipality => 当該市町村に属する全ユーザー

    戻り値のリスト要素の形式:
        {
          "continent":    "...",
          "country":      "...",
          "prefecture":   "...",
          "municipality": "...",
          "uuid":         "..." 
        }
    """
    # Partition Key (PK) = continent
    pk = continent

    # Sort Key (SK) prefix を組み立て
    # country, prefecture, municipality の順に “#” 区切りでつなぐ
    sk_prefix_parts = []
    if country:
        sk_prefix_parts.append(country)
    if prefecture:
        sk_prefix_parts.append(prefecture)
    if municipality:
        sk_prefix_parts.append(municipality)

    if sk_prefix_parts:
        # たとえば country="JP", prefecture="13", municipality="Chiyoda" => "JP#13#Chiyoda"
        sk_prefix = "#".join(sk_prefix_parts)
        # DynamoDB query: PK=continent AND SK BEGINS_WITH sk_prefix
        resp = table.query(
            KeyConditionExpression=Key("continent").eq(pk) &
                                   Key("location_uuid").begins_with(sk_prefix),
        )
    else:
        # “country も prefecture も municipality も指定なし” → 大陸だけで全件取得
        resp = table.query(
            KeyConditionExpression=Key("continent").eq(pk)
        )

    items = resp.get("Items", [])
    result = []
    for it in items:
        result.append({
            "continent":    it["continent"],
            "country":      it["country"],
            "prefecture":   it["prefecture"],
            "municipality": it["municipality"],
            "uuid":         it["uuid"],
        })
    return result
