pub mod ntru_operations {
    use ntrust_native::{crypto_kem_dec, crypto_kem_enc, crypto_kem_keypair, AesState};
    use ntrust_native::{
        CRYPTO_BYTES, CRYPTO_CIPHERTEXTBYTES, CRYPTO_PUBLICKEYBYTES, CRYPTO_SECRETKEYBYTES,
    };
    use std::error::Error;

    /// 鍵ペアを表す構造体
    pub struct NtruKeyPair {
        pub public_key: [u8; CRYPTO_PUBLICKEYBYTES],
        pub secret_key: [u8; CRYPTO_SECRETKEYBYTES],
    }

    /// 共有秘密鍵を表す構造体
    pub struct NtruSharedSecret {
        pub shared_secret: [u8; CRYPTO_BYTES],
    }

    /// 暗号文を表す構造体
    pub struct NtruCipherText {
        pub cipher_text: [u8; CRYPTO_CIPHERTEXTBYTES],
    }

    /// 鍵ペアを生成
    pub fn generate_keypair() -> Result<NtruKeyPair, Box<dyn Error>> {
        let mut rng = AesState::new();
        let mut public_key = [0u8; CRYPTO_PUBLICKEYBYTES];
        let mut secret_key = [0u8; CRYPTO_SECRETKEYBYTES];

        // 鍵ペア生成関数の呼び出し
        crypto_kem_keypair(&mut public_key, &mut secret_key, &mut rng)
            .map_err(|_| "Failed to generate keypair")?;

        Ok(NtruKeyPair {
            public_key,
            secret_key,
        })
    }

    /// 暗号化を実行
    pub fn encrypt(
        public_key: &[u8; CRYPTO_PUBLICKEYBYTES],
    ) -> Result<(NtruCipherText, NtruSharedSecret), Box<dyn Error>> {
        let mut rng = AesState::new();
        let mut cipher_text = [0u8; CRYPTO_CIPHERTEXTBYTES];
        let mut shared_secret = [0u8; CRYPTO_BYTES];

        // 暗号化関数の呼び出し
        crypto_kem_enc(&mut cipher_text, &mut shared_secret, public_key, &mut rng)
            .map_err(|_| "Failed to encrypt")?;

        Ok((
            NtruCipherText { cipher_text },
            NtruSharedSecret { shared_secret },
        ))
    }

    /// 復号を実行
    pub fn decrypt(
        cipher_text: &[u8; CRYPTO_CIPHERTEXTBYTES],
        secret_key: &[u8; CRYPTO_SECRETKEYBYTES],
    ) -> Result<NtruSharedSecret, Box<dyn Error>> {
        let mut shared_secret = [0u8; CRYPTO_BYTES];

        // 復号関数の呼び出し
        crypto_kem_dec(&mut shared_secret, cipher_text, secret_key)
            .map_err(|_| "Failed to decrypt")?;

        Ok(NtruSharedSecret { shared_secret })
    }
}
