// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\core_stub.rs
//! 最低限のダミー LDPC 実装（1シャード＝原文）

use std::io;

pub trait ErasureCoder: Send + Sync + 'static {
    fn encode(&self, data: &[u8], _: usize, _: usize)
        -> Result<Vec<Vec<u8>>, io::Error>;
    fn decode(&self,
              shards: Vec<Option<Vec<u8>>>,
              _: usize, _: usize)
        -> Result<Vec<u8>, io::Error>;
}

#[derive(Clone)]
pub struct LDPCEncoder;
impl LDPCEncoder { pub fn new(_: (), _: u64) -> Self { Self } }
impl ErasureCoder for LDPCEncoder {
    fn encode(&self, d: &[u8], _k: usize, _m: usize)
        -> Result<Vec<Vec<u8>>, io::Error>
    { Ok(vec![d.to_vec()]) }                     // そのまま 1 本
    fn decode(&self, mut s: Vec<Option<Vec<u8>>>, _k: usize, _m: usize)
        -> Result<Vec<u8>, io::Error>
    { Ok(s.remove(0).flatten().unwrap_or_default()) }
}

pub mod decoder {
    pub mod peeling {
        use super::super::{ErasureCoder};
        #[derive(Clone)]
        pub struct PeelingDecoder;
        impl PeelingDecoder { pub fn new(_: (), _: usize, _: usize) -> Self { Self } }
        impl ErasureCoder for PeelingDecoder {
            fn encode(&self, _: &[u8], _: usize, _: usize)
                -> Result<Vec<Vec<u8>>, std::io::Error> { unreachable!() }
            fn decode(&self,
                      shards: Vec<Option<Vec<u8>>>,
                      _: usize, _: usize)
                -> Result<Vec<u8>, std::io::Error>
            { Ok(shards.into_iter().flatten().next().unwrap_or_default()) }
        }
    }
}
