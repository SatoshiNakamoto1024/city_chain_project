// D:\city_chain_project\DAGs\libs\algorithm\rvh_weighted\src\main_weighted.rs
//! `cargo run --bin main_weighted -- -n "n1:1000:50,n2:600:80" -k tx01 -c 1`

use clap::{Parser, Subcommand};
use rvh_weighted::{weighted_select, NodeInfo};

#[derive(Parser)]
struct Cli {
    /// nodeId:stake:capacityMB:rtt のカンマ区切り
    #[arg(long)]
    nodes: String,
    #[arg(long)]
    key: String,
    #[arg(long)]
    count: usize,
}

fn main() {
    let cli = Cli::parse();
    let infos: Vec<NodeInfo> = cli.nodes.split(',')
        .map(|s| {
            let parts: Vec<_> = s.split(':').collect();
            NodeInfo::new(parts[0],       // id
                          parts[1].parse().unwrap_or(0),
                          parts[2].parse().unwrap_or(0),
                          parts.get(3).and_then(|v| v.parse().ok()).unwrap_or(20.0))
        })
        .collect();

    match weighted_select(&infos, &cli.key, cli.count) {
        Ok(sel) => println!("selected = {:?}", sel),
        Err(e)  => eprintln!("Error: {e}"),
    }
}
