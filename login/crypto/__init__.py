# crypto/__init__.py
"""
crypto パッケージの初期化ファイルです。
ntru, rsa, dilithium の各モジュールをエクスポートします。
"""
from .ntru import encrypt, decrypt
from .rsa import encrypt as rsa_encrypt, decrypt as rsa_decrypt
from .dilithium import sign, verify
