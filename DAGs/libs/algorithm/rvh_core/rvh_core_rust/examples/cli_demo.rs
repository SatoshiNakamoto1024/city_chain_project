// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\examples\cli_demo.rs
//! cargo run --example cli_demo -- --nodes n1,n2,n3 --key myobj --k 2

use clap::Parser;
use rvh_core_rust::rendezvous::rendezvous_hash;

#[derive(Parser)]
struct Opts {
    #[arg(long)]
    nodes: String,
    #[arg(long)]
    key: String,
    #[arg(long)]
    k: usize,
}

fn main() {
    let opts = Opts::parse();
    let nodes: Vec<String> = opts.nodes.split(',').map(str::to_owned).collect();
    match rendezvous_hash(&nodes, &opts.key, opts.k) {
        Ok(sel) => println!("Selected: {}", sel.join(",")),
        Err(e)  => eprintln!("Error: {e}"),
    }
}
