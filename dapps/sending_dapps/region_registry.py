# sending_dapps/region_registry.py
"""
region_registry.py

大陸ごとの DAG サーバー URL と MongoDB URI、AWS リージョンを定義しています。
本番環境ではここに実際のエンドポイントを設定してください。
"""

REGION_SERVERS = {
    "Asia": {
        "dag_url":    "https://asia-dag.example.com/api/dag/add_transaction",
        "mongo_uri":  "mongodb://mongo-asia:13024/Asia_journal_entries",
        "aws_region": "ap-northeast-1"
    },
    "Europe": {
        "dag_url":    "https://europe-dag.example.com/api/dag/add_transaction",
        "mongo_uri":  "mongodb://mongo-europe:13025/Europe_journal_entries",
        "aws_region": "eu-central-1"
    },
    "Africa": {
        "dag_url":    "https://africa-dag.example.com/api/dag/add_transaction",
        "mongo_uri":  "mongodb://mongo-africa:13027/Africa_journal_entries",
        "aws_region": "af-south-1"
    },
    "NorthAmerica": {
        "dag_url":    "https://na-dag.example.com/api/dag/add_transaction",
        "mongo_uri":  "mongodb://mongo-northamerica:13028/NorthAmerica_journal_entries",
        "aws_region": "us-east-1"
    },
    "SouthAmerica": {
        "dag_url":    "https://sa-dag.example.com/api/dag/add_transaction",
        "mongo_uri":  "mongodb://mongo-southamerica:13029/SouthAmerica_journal_entries",
        "aws_region": "sa-east-1"
    },
    "Oceania": {
        "dag_url":    "https://oceania-dag.example.com/api/dag/add_transaction",
        "mongo_uri":  "mongodb://mongo-australia:13026/Oceania_journal_entries",
        "aws_region": "ap-southeast-2"
    },
    "Antarctica": {
        "dag_url":    "https://antarctica-dag.example.com/api/dag/add_transaction",
        "mongo_uri":  "mongodb://mongo-antarctica:13030/Antarctica_journal_entries",
        "aws_region": "us-east-1"
    },
    "Default": {
        "dag_url":    "https://default-dag.example.com/api/dag/add_transaction",
        "mongo_uri":  "mongodb://mongo-default:13000/Default_journal_entries",
        "aws_region": "us-east-1"
    }
}

def get_region_config(continent: str) -> dict:
    """
    大陸コード (Asia, Europe, ...) を受け取って、
    REGION_SERVERS に登録された設定を返す。なければ Default を返す。
    """
    return REGION_SERVERS.get(continent, REGION_SERVERS["Default"])
