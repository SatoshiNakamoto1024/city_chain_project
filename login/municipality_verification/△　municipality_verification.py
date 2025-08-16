# municipality_verification/municipality_verification.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
from municipality_verification.config import AWS_REGION, DYNAMODB_TABLE

# DynamoDB
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(DYNAMODB_TABLE)

def get_pending_users():
    response = users_table.scan(
        FilterExpression="approval_status = :status",
        ExpressionAttributeValues={":status": "pending"}
    )
    return response.get("Items", [])


def approve_user(uuid):
    users_table.update_item(
        Key={"uuid": uuid, "session_id": "REGISTRATION"},
        UpdateExpression="SET approval_status = :status",
        ExpressionAttributeValues={":status": "approved"}
    )


def reject_user(uuid):
    users_table.update_item(
        Key={"uuid": uuid, "session_id": "REGISTRATION"},
        UpdateExpression="SET approval_status = :status",
        ExpressionAttributeValues={":status": "rejected"}
    )
