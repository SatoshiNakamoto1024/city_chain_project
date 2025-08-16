# mapping_continental_municipality/services.py
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
from boto3.dynamodb.conditions import Key, Attr
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
    UserLocationMapping テーブルに登録する。
    もしすでに同じ UUID のマッピングがあれば古いものを削除してから新規登録する。

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
    # 1) 既存のマッピングを探して削除する
    #    → テーブル全体をスキャンし、「uuid 属性 == 指定の uuid」と一致するものを削除
    try:
        scan_resp = table.scan(
            FilterExpression=Attr("uuid").eq(uuid)
        )
        items_to_delete = scan_resp.get("Items", [])
        # スキャン結果は複数ページになる可能性があるため、LastEvaluatedKey があればループ
        while "LastEvaluatedKey" in scan_resp:
            scan_resp = table.scan(
                ExclusiveStartKey=scan_resp["LastEvaluatedKey"],
                FilterExpression=Attr("uuid").eq(uuid)
            )
            items_to_delete.extend(scan_resp.get("Items", []))

        for itm in items_to_delete:
            table.delete_item(
                Key={
                    "continent": itm["continent"],
                    "location_uuid": itm["location_uuid"]
                }
            )
    except Exception as e:
        # スキャンや削除に関しては「存在しない場合」などでも例外が発生しうるので、
        # ログ等はここで吐いておくと良いが、削除失敗だけで新規登録を止めたくない場合は pass
        # raise e  # 必要に応じて例外を外に投げる

        # 本番環境ではログを取ることを推奨
        print(f"[WARN] set_user_location_mapping - 既存削除中にエラー発生: {e}")

    # 2) 新しいマッピングを登録
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
    pk = continent
    sk_prefix_parts = []
    if country:
        sk_prefix_parts.append(country)
    if prefecture:
        sk_prefix_parts.append(prefecture)
    if municipality:
        sk_prefix_parts.append(municipality)

    if sk_prefix_parts:
        sk_prefix = "#".join(sk_prefix_parts)
        resp = table.query(
            KeyConditionExpression=Key("continent").eq(pk) &
                                   Key("location_uuid").begins_with(sk_prefix),
        )
    else:
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
