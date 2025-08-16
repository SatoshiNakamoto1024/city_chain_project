# D:\city_chain_project\ntru\rsa-sing-py\app_sing.py
from rsa_sign import generate_keypair, sign_message, verify_signature
from cryptography.hazmat.primitives import serialization

class DAppsRSASignHandler:
    def __init__(self, key_size=2048):
        self.private_key, self.public_key = generate_keypair(key_size)

    def save_keys(self):
        # Save the private key to a file
        with open("private_key.pem", "wb") as private_file:
            private_file.write(
                self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # Save the public key to a file
        with open("public_key.pem", "wb") as public_file:
            public_file.write(
                self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )

def main():
    print("Initializing DApps RSA Sign Handler...")
    dapps_rsa_handler = DAppsRSASignHandler()

    print("Saving RSA keys...")
    dapps_rsa_handler.save_keys()

    # Example signing and verification
    message = "DApps transaction example"
    print(f"Original message: {message}")

    signature = sign_message(dapps_rsa_handler.private_key, message)
    print(f"Generated signature: {signature.hex()}")

    is_valid = verify_signature(dapps_rsa_handler.public_key, message, signature)
    if is_valid:
        print("Signature verification successful!")
    else:
        print("Signature verification failed.")

if __name__ == "__main__":
    main()
