from pymongo_handler import MongoDBHandler

def main():
    # MongoDB接続情報
    uri = "mongodb://localhost:27017/"
    database_name = "test_data"
    collection_name = "transactions"

    # MongoDBハンドラの初期化
    db_handler = MongoDBHandler(uri, database_name)

    try:
        # データの挿入
        document = {
            "user": "Alice",
            "action": "send",
            "amount": 100,  # Rust の Int32 に対応
            "status": "pending"
        }
        inserted_id = db_handler.insert_document(collection_name, document)
        print(f"Document inserted with ID: {inserted_id}")

        # データの取得
        query = {"user": "Alice"}
        result = db_handler.find_document(collection_name, query)
        if result:
            print(f"Found document: {result}")
        else:
            print("No document found with the given query.")

        # データの更新
        update = {"status": "completed"}
        updated_count = db_handler.update_document(collection_name, query, update)
        print(f"Number of documents updated: {updated_count}")

        # すべてのデータをリスト
        all_documents = db_handler.list_documents(collection_name)
        print(f"All documents: {all_documents}")

        # データの削除
        deleted_count = db_handler.delete_document(collection_name, query)
        print(f"Number of documents deleted: {deleted_count}")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # 接続を閉じる
        db_handler.close_connection()

if __name__ == "__main__":
    main()
