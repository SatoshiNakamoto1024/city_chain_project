import boto3
import uuid
from datetime import datetime

session = boto3.Session(profile_name="satoshi-dev", region_name="us-east-1")
dynamodb = session.resource("dynamodb")
table = dynamodb.Table("UsersTable")

# CRUD テスト用データ
test_uuid = str(uuid.uuid4())
test_item = {
    "uuid": test_uuid,
    "session_id": "TEST",
    "username": "test_user",
    "email": "test@example.com",
    "created_at": datetime.utcnow().isoformat() + "Z"
}

def create_item():
    table.put_item(Item=test_item)
    print(f"✅ 登録完了 (uuid: {test_uuid})")

def read_item():
    response = table.get_item(Key={"uuid": test_uuid, "session_id": "TEST"})
    item = response.get("Item")
    if item:
        print("🔍 取得成功:", item)
    else:
        print("❌ 取得できませんでした")

def update_item():
    table.update_item(
        Key={"uuid": test_uuid, "session_id": "TEST"},
        UpdateExpression="SET username = :val",
        ExpressionAttributeValues={":val": "updated_user"}
    )
    print("🛠️ 更新完了")

def delete_item():
    table.delete_item(Key={"uuid": test_uuid, "session_id": "TEST"})
    print("🗑️ 削除完了")

if __name__ == "__main__":
    create_item()
    read_item()
    update_item()
    read_item()
    delete_item()
