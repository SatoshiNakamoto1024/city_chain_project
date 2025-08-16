// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\trait_extensions.rs
//! Convenience extensions for any `ErasureCoder` plugin.
//!
//! Provides methods to encode/decode directly from owned `Vec<u8>` or
//! `Vec<Option<Vec<u8>>>`, forwarding through your configured codec.

use crate::core::erasure_coder::{ErasureCoder, ECError};
use crate::ECConfig;

/// Extra methods that any `ErasureCoder` may call directly.
pub trait ErasureExt: ErasureCoder {
    /// Encode from an owned `Vec<u8>`, using the provided config.
    ///
    /// # Errors
    ///
    /// Returns any `ECError` thrown by the underlying codec.
    fn encode_vec(
        &self,
        data: Vec<u8>,
        cfg: &ECConfig,
    ) -> Result<Vec<Vec<u8>>, ECError> {
        self.encode(&data, cfg)
    }

    /// Decode from a `Vec<Option<Vec<u8>>>` (where `None` = missing shard).
    ///
    /// # Errors
    ///
    /// Returns any `ECError` thrown by the underlying codec.
    fn decode_vec(
        &self,
        shards: Vec<Option<Vec<u8>>>,
        cfg: &ECConfig,
    ) -> Result<Vec<u8>, ECError> {
        self.decode(shards, cfg)
    }
}

// Blanket impl for all ErasureCoder types
impl<T: ErasureCoder> ErasureExt for T {}
