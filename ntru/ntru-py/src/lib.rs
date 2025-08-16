// src/lib.rs
use pyo3::types::PyBytes;
use pyo3::prelude::*;
use pyo3::exceptions;
use ntrust_native::{crypto_kem_dec, crypto_kem_enc, crypto_kem_keypair, AesState};
use ntrust_native::{
    CRYPTO_BYTES, CRYPTO_CIPHERTEXTBYTES, CRYPTO_PUBLICKEYBYTES, CRYPTO_SECRETKEYBYTES,
};

/// 鍵ペアを表す構造体
#[pyclass]
pub struct NtruKeyPair {
    pub public_key: Vec<u8>,
    pub secret_key: Vec<u8>,
}

#[pymethods]
impl NtruKeyPair {
    #[getter]
    pub fn public_key<'py>(&self, py: pyo3::Python<'py>) -> &'py PyBytes {
        PyBytes::new(py, &self.public_key)
    }

    #[getter]
    pub fn secret_key<'py>(&self, py: pyo3::Python<'py>) -> &'py PyBytes {
        PyBytes::new(py, &self.secret_key)
    }
}

/// 共有秘密鍵を表す構造体
#[pyclass]
pub struct NtruSharedSecret {
    pub shared_secret: Vec<u8>,
}

#[pymethods]
impl NtruSharedSecret {
    #[getter]
    pub fn shared_secret<'py>(&self, py: pyo3::Python<'py>) -> &'py PyBytes {
        PyBytes::new(py, &self.shared_secret)
    }
}

/// 暗号文を表す構造体
#[pyclass]
pub struct NtruCipherText {
    pub cipher_text: Vec<u8>,
}

#[pymethods]
impl NtruCipherText {
    #[getter]
    pub fn cipher_text<'py>(&self, py: pyo3::Python<'py>) -> &'py PyBytes {
        PyBytes::new(py, &self.cipher_text)
    }
}

/// 鍵ペア生成関数
#[pyfunction]
fn generate_keypair(py: Python) -> PyResult<NtruKeyPair> {
    let mut rng = AesState::new();
    let mut public_key = [0u8; CRYPTO_PUBLICKEYBYTES];
    let mut secret_key = [0u8; CRYPTO_SECRETKEYBYTES];

    // 鍵ペア生成関数の呼び出し
    crypto_kem_keypair(&mut public_key, &mut secret_key, &mut rng)
        .map_err(|_| exceptions::PyRuntimeError::new_err("Failed to generate keypair"))?;

    Ok(NtruKeyPair {
        public_key: public_key.to_vec(),
        secret_key: secret_key.to_vec(),
    })
}

/// 暗号化関数
#[pyfunction]
fn encrypt<'py>(
    py: Python<'py>,
    public_key: &PyBytes,
) -> PyResult<(&'py PyBytes, &'py PyBytes)> {
    let public_key_vec = public_key.as_bytes();

    if public_key_vec.len() != CRYPTO_PUBLICKEYBYTES {
        return Err(exceptions::PyValueError::new_err("Invalid public key length"));
    }

    let public_key_array: &[u8; CRYPTO_PUBLICKEYBYTES] = public_key_vec
        .try_into()
        .map_err(|_| exceptions::PyValueError::new_err("Failed to convert public_key to array"))?;

    let mut rng = AesState::new();
    let mut cipher_text = [0u8; CRYPTO_CIPHERTEXTBYTES];
    let mut shared_secret = [0u8; CRYPTO_BYTES];

    crypto_kem_enc(&mut cipher_text, &mut shared_secret, public_key_array, &mut rng)
        .map_err(|_| exceptions::PyRuntimeError::new_err("Failed to encrypt"))?;

    let cipher_text_bytes = PyBytes::new(py, &cipher_text);
    let shared_secret_bytes = PyBytes::new(py, &shared_secret);

    Ok((cipher_text_bytes, shared_secret_bytes))
}

/// 復号関数
#[pyfunction]
fn decrypt<'py>(
    py: Python<'py>,
    cipher_text: &PyBytes,
    secret_key: &PyBytes,
) -> PyResult<&'py PyBytes> {
    let cipher_text_vec = cipher_text.as_bytes();
    let secret_key_vec = secret_key.as_bytes();

    if cipher_text_vec.len() != CRYPTO_CIPHERTEXTBYTES {
        return Err(exceptions::PyValueError::new_err("Invalid ciphertext length"));
    }

    if secret_key_vec.len() != CRYPTO_SECRETKEYBYTES {
        return Err(exceptions::PyValueError::new_err("Invalid secret key length"));
    }

    let cipher_text_array: &[u8; CRYPTO_CIPHERTEXTBYTES] = cipher_text_vec
        .try_into()
        .map_err(|_| exceptions::PyValueError::new_err("Failed to convert cipher_text to array"))?;

    let secret_key_array: &[u8; CRYPTO_SECRETKEYBYTES] = secret_key_vec
        .try_into()
        .map_err(|_| exceptions::PyValueError::new_err("Failed to convert secret_key to array"))?;

    let mut shared_secret = [0u8; CRYPTO_BYTES];

    crypto_kem_dec(&mut shared_secret, cipher_text_array, secret_key_array)
        .map_err(|_| exceptions::PyRuntimeError::new_err("Failed to decrypt"))?;

    let shared_secret_bytes = PyBytes::new(py, &shared_secret);

    Ok(shared_secret_bytes)
}

/// モジュールの定義
#[pymodule]
fn ntrust_native_py(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<NtruKeyPair>()?;
    m.add_class::<NtruSharedSecret>()?;
    m.add_class::<NtruCipherText>()?;
    m.add_function(wrap_pyfunction!(generate_keypair, m)?)?;
    m.add_function(wrap_pyfunction!(encrypt, m)?)?;
    m.add_function(wrap_pyfunction!(decrypt, m)?)?;
    Ok(())
}
