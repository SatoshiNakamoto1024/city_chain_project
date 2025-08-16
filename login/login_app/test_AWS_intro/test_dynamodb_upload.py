#!/usr/bin/env python3
import os
import boto3
from botocore.exceptions import ClientError

def main():
    # DynamoDB のテーブル名 (環境変数がなければ "UsersTable" を使用)
    table_name = os.getenv("DYNAMODB_TABLE", "UsersTable")
    
    # AWS リージョンは "us-east-1"（必要に応じて変更してください）
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)
    
    # テスト用のアイテムを定義（テーブルのプライマリキーが "uuid" であると仮定）
    test_item = {
        "uuid": "test_item_123",           # プライマリキーは "uuid" にする
        "session_id": "session_1",       # ソートキー（任意の値を設定）
        "name": "Test User",
        "birth_date": "2000-01-01",
        "address": "123 Test Street",
        "mynumber": "123456789012",
        "email": "test@example.com",
        "phone": "123-456-7890",
        "initial_harmony_token": 100,
        "created_at": "20250320T123456Z"
    }
    
    # アイテムの保存 (PutItem)
    try:
        table.put_item(Item=test_item)
        print("Successfully uploaded test item to DynamoDB.")
    except ClientError as e:
        print("Error uploading test item:", e)
        return
    
    # アイテムの取得 (GetItem)
    try:
        response = table.get_item(Key={"uuid": "test_item_123", "session_id": "session_1"})
        item = response.get("Item")
        if item:
            print("Successfully downloaded test item from DynamoDB:")
            print(item)
        else:
            print("Test item not found.")
    except ClientError as e:
        print("Error downloading test item:", e)
        return

if __name__ == "__main__":
    main()
