# crypto/__init__.py

# 本番用：暗号モジュールまとめ

from .ntru import NtruEncryption
from .dilithium import create_keypair, sign_message, verify_signature
