# client_cert/models.py

# クライアント証明書 JSON の構造

"""
{
  "uuid": "ユーザーID",
  "ntru_public": "NTRU公開鍵（base64または文字列）",
  "dilithium_public": "Dilithium公開鍵（hex）",
  "valid_from": "2025-04-01T00:00:00Z",
  "valid_to": "2026-04-01T00:00:00Z",
  "issuer": "CustomCA v1",
  "signed_at": "署名日時（ISO）",
  "signature": "署名（NTRU暗号による）"
}
"""
