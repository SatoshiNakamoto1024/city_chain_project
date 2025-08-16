# tests/test_qr_decode.py
import base64, json, textwrap

QR_STR = """
ここに QR スキャンで得た Base64 文字列を貼り付ける
""".strip()

try:
    data = json.loads(base64.b64decode(QR_STR))
    print("✅ Decode OK")
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print("❌ デコード失敗:", e)
