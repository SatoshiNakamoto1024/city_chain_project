// D:\city_chain_project\DAGs\libs\algorithm\rvh_simd\src\main_simd.rs
//! シンプルな CLI：node と key を与えて 128bit スコアを表示
//! `cargo run --features cli -- -n node1 -k tx42`

#![cfg(feature = "cli")]

use clap::Parser;
use rvh_simd::score_u128_simd;

#[derive(Parser)]
struct Opt {
    #[clap(short, long)]
    node: String,
    #[clap(short, long)]
    key:  String,
}

fn main() {
    let opt = Opt::parse();
    match score_u128_simd(&opt.node, &opt.key) {
        Ok(score) => println!("{score:#034x}"),
        Err(e)    => eprintln!("Error: {e}"),
    }
}
