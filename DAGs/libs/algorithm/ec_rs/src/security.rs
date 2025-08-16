// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\security.rs
//! Security utilities: keyed randomness & secure zeroization.

use crate::ECConfig;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use zeroize::Zeroize;

type HmacSha256 = Hmac<Sha256>;

/// Manages HMAC‐based keyed randomness for downstream uses.
pub struct Security {
    mac: HmacSha256,
}

impl Security {
    /// Create a new `Security` with the given key material.
    ///
    /// # Panics
    ///
    /// Panics if `key` length is invalid for HMAC‐SHA256.
    pub fn new(key: &[u8]) -> Self {
        let mac = HmacSha256::new_from_slice(key)
            .expect("Invalid HMAC key length");
        Security { mac }
    }

    /// Derive a fresh pseudorandom blob from the given `label`.
    ///
    /// Internally updates the HMAC state.
    pub fn derive(&mut self, label: &[u8]) -> Vec<u8> {
        self.mac.update(label);
        self.mac.clone().finalize().into_bytes().to_vec()
    }
}

/// Zero out all bytes in every shard buffer.
///
/// Uses the `zeroize` crate to ensure compiler will not optimize it away.
pub fn zeroize_shards(shards: &mut [Vec<u8>]) {
    for buf in shards.iter_mut() {
        buf.as_mut_slice().zeroize();
    }
}
