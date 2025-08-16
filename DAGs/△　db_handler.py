# db_handler.py
from pymongo import MongoClient
from config import MONGODB_URI, DATABASE_NAME, COLLECTION_NAME
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

def save_transaction(transaction):
    try:
        result = collection.insert_one(transaction)
        logger.info("Transaction saved: %s", result.inserted_id)
        return result.inserted_id
    except Exception as e:
        logger.error("トランザクション保存エラー: %s", e)
        return None

if __name__ == "__main__":
    sample = {"tx_id": "sample_tx", "data": "example"}
    save_transaction(sample)
