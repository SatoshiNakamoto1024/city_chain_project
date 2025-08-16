// D:\city_chain_project\Algorithm\EC\ec_rust_src\core\ldpc\src\main_ldpc.rs
use ldpc::{ErasureCoder, LDPCEncoder, LDPCDecoder};

fn main() {
    let data = b"Hello LDPC world".to_vec();
    let k = 4;
    let m = 2;
    let encoder = LDPCEncoder::new();
    let shards = encoder.encode(&data, k, m).unwrap();
    println!("Generated {} shards", shards.len());

    // Simulate loss of one shard
    let mut opt = shards.into_iter().map(Some).collect::<Vec<_>>();
    opt[0] = None;
    let decoder = LDPCDecoder::new();
    let recovered = decoder.decode(opt, k, m).unwrap();
    println!("Recovered: {}", String::from_utf8_lossy(&recovered));
}