# client_cert/table.py
import os
import boto3

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "ClientCertificates")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE", "ClientCertificates"))
