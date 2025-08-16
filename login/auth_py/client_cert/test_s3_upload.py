import boto3
import botocore

def main():
    bucket_name = "my-client-cert-bucket"
    source_key = "test.txt"  # the key where test.txt currently is (at the root of the bucket)
    destination_key = "user_client_cert/test.txt"  

    # Create an S3 client.
    # Make sure your AWS credentials are set in your environment or via the AWS CLI configuration.
    s3 = boto3.client("s3", region_name="us-east-1")  # adjust region as needed

    # Download the object from S3.
    try:
        response = s3.get_object(Bucket=bucket_name, Key=source_key)
        file_data = response["Body"].read()
        print("Successfully downloaded 'test.txt'.")
    except botocore.exceptions.ClientError as e:
        print("Error downloading 'test.txt':", e)
        return

    # Upload the file to the new destination.
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=destination_key,
            Body=file_data,
            ContentType="text/plain"  # adjust if needed
        )
        print(f"Successfully uploaded 'test.txt' to '{destination_key}'.")
    except botocore.exceptions.ClientError as e:
        print("Error uploading file:", e)
        return

if __name__ == "__main__":
    main()
