import unittest
from pymongo_handler import MongoDBHandler


class TestMongoDBHandler(unittest.TestCase):
    def setUp(self):
        # テスト用MongoDB接続情報
        self.uri = "mongodb://localhost:27017/"
        self.database_name = "test_database"
        self.collection_name = "test_collection"
        self.db_handler = MongoDBHandler(self.uri, self.database_name)

        # テスト用データの準備
        self.test_document = {
            "user": "TestUser",
            "action": "test",
            "amount": 50,  # Rustの`Int32`と互換性のある数値型
            "status": "pending"
        }

    def tearDown(self):
        # テスト用コレクションをクリア
        self.db_handler.db[self.collection_name].delete_many({})
        self.db_handler.close_connection()

    def test_insert_and_find_document(self):
        # データの挿入
        inserted_id = self.db_handler.insert_document(self.collection_name, self.test_document)
        self.assertIsNotNone(inserted_id, "Document insertion failed")

        # 挿入されたデータの取得
        result = self.db_handler.find_document(self.collection_name, {"user": "TestUser"})
        self.assertIsNotNone(result, "Document not found")
        self.assertEqual(result["user"], "TestUser", "Inserted document does not match")
        self.assertEqual(result["amount"], 50, "Inserted document amount mismatch")

    def test_update_document(self):
        # データの挿入
        self.db_handler.insert_document(self.collection_name, self.test_document)

        # データの更新
        updated_count = self.db_handler.update_document(
            self.collection_name,
            {"user": "TestUser"},
            {"amount": 100}  # Rustの`Int32`に合わせた値
        )
        self.assertEqual(updated_count, 1, "Document update failed")

        # 更新されたデータの取得と確認
        result = self.db_handler.find_document(self.collection_name, {"user": "TestUser"})
        self.assertIsNotNone(result, "Updated document not found")
        self.assertEqual(result["amount"], 100, "Updated document amount mismatch")

    def test_delete_document(self):
        # データの挿入
        self.db_handler.insert_document(self.collection_name, self.test_document)

        # データの削除
        deleted_count = self.db_handler.delete_document(self.collection_name, {"user": "TestUser"})
        self.assertEqual(deleted_count, 1, "Document deletion failed")

        # 削除されたことを確認
        result = self.db_handler.find_document(self.collection_name, {"user": "TestUser"})
        self.assertIsNone(result, "Document was not deleted")

    def test_list_documents(self):
        # データを複数挿入
        self.db_handler.insert_document(self.collection_name, self.test_document)
        self.db_handler.insert_document(self.collection_name, {
            "user": "AnotherUser",
            "action": "test",
            "amount": 30,
            "status": "pending"
        })

        # データのリスト取得
        all_documents = self.db_handler.list_documents(self.collection_name)
        self.assertEqual(len(all_documents), 2, "Document listing failed")
        self.assertTrue(any(doc["user"] == "TestUser" for doc in all_documents), "TestUser document not found")
        self.assertTrue(any(doc["user"] == "AnotherUser" for doc in all_documents), "AnotherUser document not found")


if __name__ == "__main__":
    unittest.main()
