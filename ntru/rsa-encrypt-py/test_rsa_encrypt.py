# test_rsa_encrypt.py
import unittest
from rsa_encrypt import generate_keypair, encrypt_message, decrypt_message
import base64

class TestRSAEncryption(unittest.TestCase):

    def test_encryption_decryption(self):
        # 鍵ペアの生成
        private_key, public_key = generate_keypair()

        # テストメッセージ
        message = "Test Message"

        # メッセージの暗号化
        encrypted_message = encrypt_message(public_key, message)
        encoded_encrypted_message = base64.b64encode(encrypted_message).decode('utf-8')

        # メッセージの復号化
        decoded_encrypted_message = base64.b64decode(encoded_encrypted_message.encode('utf-8'))
        decrypted_message = decrypt_message(private_key, decoded_encrypted_message)

        # 復号化されたメッセージが元のメッセージと一致することを確認
        self.assertEqual(decrypted_message, message)

    def test_invalid_decryption(self):
        # 鍵ペアの生成
        private_key, public_key = generate_keypair()

        # 別の鍵ペアを生成
        other_private_key, other_public_key = generate_keypair()

        # テストメッセージ
        message = "Test Message"

        # メッセージの暗号化
        encrypted_message = encrypt_message(public_key, message)

        # 異なる秘密鍵での復号化を試みる
        with self.assertRaises(ValueError):
            decrypt_message(other_private_key, encrypted_message)

if __name__ == '__main__':
    unittest.main()
