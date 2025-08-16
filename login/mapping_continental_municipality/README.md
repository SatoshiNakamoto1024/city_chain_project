テーブルアイテム例
例えば、以下の３つのユーザーがいたとき：

continent	country	prefecture	municipality	uuid
"Asia"	"JP"	"13"	"Chiyoda"	"user-abc"
"Asia"	"JP"	"13"	"Shinjuku"	"user-def"
"Europe"	"FR"	"IDF"	"Paris"	"user-ghi"

それぞれを１アイテムずつ、以下のように保存します。
// アイテム 1
{
  "continent":      "Asia",
  "location_uuid":  "JP#13#Chiyoda#user-abc",
  "country":        "JP",
  "prefecture":     "13",
  "municipality":   "Chiyoda",
  "uuid":           "user-abc"
}

// アイテム 2
{
  "continent":      "Asia",
  "location_uuid":  "JP#13#Shinjuku#user-def",
  "country":        "JP",
  "prefecture":     "13",
  "municipality":   "Shinjuku",
  "uuid":           "user-def"
}

// アイテム 3
{
  "continent":      "Europe",
  "location_uuid":  "FR#IDF#Paris#user-ghi",
  "country":        "FR",
  "prefecture":     "IDF",
  "municipality":   "Paris",
  "uuid":           "user-ghi"
}

PK（continent） が同じアイテムはまとめてパーティションに格納されます。
SK（location_uuid） の先頭部分を絞り込むことで、

「Asia 全体のアイテム」→ Query(KeyCondition=continent="Asia")
「Asia の中の JP 全体」→ Query(KeyCondition=continent="Asia" AND begins_with(location_uuid, "JP"))
「Asia, JP, 13 全体」→ Query(KeyCondition=continent="Asia" AND begins_with(location_uuid, "JP#13"))
「Asia, JP, 13, Chiyoda 全体」→ Query(KeyCondition=continent="Asia" AND begins_with(location_uuid, "JP#13#Chiyoda"))
といった形で簡単に階層的絞り込みができるようになります。

まとめ
テーブル名：UserLocationMapping
Partition Key (PK)：continent (String)
Sort Key (SK)：location_uuid (String)
※ フォーマット例："{country}#{prefecture}#{municipality}#{uuid}"
上記の構成でテーブルを作成すれば、mapping_continental_municipality モジュールの services.py → set_user_location_mapping / get_users_by_location が正しく動作するようになります。


