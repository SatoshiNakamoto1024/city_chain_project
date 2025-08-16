# session_manager/create_login_table.py

import boto3
from botocore.exceptions import ClientError

def create_login_history_table(region_name="us-east-1", table_name="LoginHistory"):
    """
    DynamoDB上に LoginHistory テーブルを作成する。既に存在する場合は何もしない。
    """
    dynamodb = boto3.resource('dynamodb', region_name=region_name)
    try:
        table = dynamodb.Table(table_name)
        table.load()
        print(f"テーブル '{table_name}' は既に存在します。")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"テーブル '{table_name}' が存在しません。作成します...")
            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': 'uuid', 'KeyType': 'HASH'},
                    {'AttributeName': 'session_id', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'uuid', 'AttributeType': 'S'},
                    {'AttributeName': 'session_id', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
            print(f"テーブル '{table_name}' の作成が完了しました。")
        else:
            raise
    return table

if __name__ == "__main__":
    create_login_history_table()
