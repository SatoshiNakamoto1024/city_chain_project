from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure
from bson.objectid import ObjectId
from typing import Union, List, Dict

class MongoDBHandler:
    def __init__(self, uri: str, database_name: str):
        """
        Initializes the MongoDBHandler.
        """
        try:
            self.client = MongoClient(uri)
            self.db = self.client[database_name]
        except ServerSelectionTimeoutError as e:
            raise Exception(f"Failed to connect to MongoDB: {e}")

    def _validate_document(self, document: dict):
        """
        Validates the document to ensure compatibility with Rust BSON parsing.
        """
        for key, value in document.items():
            if isinstance(value, int) and not (-2**31 <= value < 2**31):
                raise ValueError(f"Field '{key}' has an integer value out of Int32 range.")
            if isinstance(value, float) and not isinstance(value, (int, float)):
                raise ValueError(f"Field '{key}' has a non-numeric float value.")

    def insert_document(self, collection_name: str, document: Dict[str, Union[str, int, float, dict, list]]):
        """
        Inserts a single document into a collection.
        """
        try:
            self._validate_document(document)
            collection = self.db[collection_name]
            result = collection.insert_one(document)
            return result.inserted_id
        except OperationFailure as e:
            raise Exception(f"Failed to insert document: {e}")
        except ValueError as e:
            raise Exception(f"Validation error: {e}")

    def find_document(self, collection_name: str, query: Dict[str, Union[str, int, float]]):
        """
        Finds a single document based on the query.
        """
        try:
            collection = self.db[collection_name]
            return collection.find_one(query)
        except OperationFailure as e:
            raise Exception(f"Failed to find document: {e}")

    def update_document(self, collection_name: str, query: Dict[str, Union[str, int, float]], update: Dict[str, Union[str, int, float]]):
        """
        Updates a single document that matches the query.
        """
        try:
            self._validate_document(update)
            collection = self.db[collection_name]
            result = collection.update_one(query, {"$set": update})
            return result.modified_count
        except OperationFailure as e:
            raise Exception(f"Failed to update document: {e}")
        except ValueError as e:
            raise Exception(f"Validation error: {e}")

    def delete_document(self, collection_name: str, query: Dict[str, Union[str, int, float]]):
        """
        Deletes a single document that matches the query.
        """
        try:
            collection = self.db[collection_name]
            result = collection.delete_one(query)
            return result.deleted_count
        except OperationFailure as e:
            raise Exception(f"Failed to delete document: {e}")

    def list_documents(self, collection_name: str) -> List[dict]:
        """
        Lists all documents in a collection.
        """
        try:
            collection = self.db[collection_name]
            return list(collection.find())
        except OperationFailure as e:
            raise Exception(f"Failed to list documents: {e}")

    def close_connection(self):
        """
        Closes the connection to MongoDB.
        """
        self.client.close()

# Example usage:
if __name__ == "__main__":
    handler = MongoDBHandler("mongodb://localhost:27017/", "test_database")

    # Insert a document
    doc = {
        "user": "Alice",
        "action": "send",
        "amount": 100,
        "status": "pending"
    }
    inserted_id = handler.insert_document("transactions", doc)
    print(f"Inserted document ID: {inserted_id}")

    # Fetch the document
    query = {"user": "Alice"}
    document = handler.find_document("transactions", query)
    print(f"Found document: {document}")

    # Update the document
    update = {"status": "completed"}
    modified_count = handler.update_document("transactions", query, update)
    print(f"Modified documents count: {modified_count}")

    # List all documents
    documents = handler.list_documents("transactions")
    print(f"All documents: {documents}")

    # Delete the document
    deleted_count = handler.delete_document("transactions", query)
    print(f"Deleted documents count: {deleted_count}")

    handler.close_connection()
