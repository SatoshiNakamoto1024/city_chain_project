# test_put.py
import os, uuid, datetime as dt, boto3, pprint

TABLE = os.getenv("DYNAMODB_TABLE", "UsersTable")
REGION = os.getenv("AWS_REGION", "us-east-1")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
tbl = dynamodb.Table(TABLE)

now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
test_uuid = f"ping-{uuid.uuid4()}"

item = {
    "uuid": test_uuid,
    "session_id": "PING",
    "created_at": now,
}

print(f"→ put_item {item!r}  to  {REGION}:{TABLE}")
tbl.put_item(Item=item)

resp = tbl.get_item(
    Key={"uuid": test_uuid, "session_id": "PING"},
    ConsistentRead=True,
)
print("← get_item result:")
pprint.pp(resp.get("Item"))

# お掃除（不要なら削除）
tbl.delete_item(Key={"uuid": test_uuid, "session_id": "PING"})
