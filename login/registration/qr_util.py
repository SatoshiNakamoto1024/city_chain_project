# registration/qr_util.py
import qrcode
import base64
import boto3
from io import BytesIO

def generate_qr_base64(data: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

def generate_qr_s3_url(data: str, uuid: str) -> str:
    """
    与えられたデータをQRコード画像化し、S3バケットにアップロードして公開URLを返す。
    """
    img = qrcode.make(data)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    s3_client = boto3.client("s3")
    bucket = "my-resister-bucket-2025"  # 本番用のS3バケット名
    key = f"qrcodes/{uuid}.png"
    s3_client.upload_fileobj(buffer, bucket, key, ExtraArgs={"ContentType": "image/png", "ACL": "public-read"})

    return f"https://{bucket}.s3.amazonaws.com/{key}"
