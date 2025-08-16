// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\src\main_rvh_core.rs
// src/main_rvh.rs

use clap::{Parser, Subcommand};
use rvh_rust::rendezvous::{rendezvous_hash, RendezvousError};

#[derive(Parser)]
#[command(name = "rvh", version, about = "Rendezvous Hash CLI")]
struct Cli {
    #[command(subcommand)]
    cmd: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Select k nodes out of a comma‐separated node list
    Select {
        /// Comma‐separated list of node IDs
        #[arg(long)]
        nodes: String,
        /// Key to hash (e.g. object ID)
        #[arg(long)]
        key: String,
        /// Number of nodes to select
        #[arg(long)]
        k: usize,
    },
}

fn main() {
    let cli = Cli::parse();
    match cli.cmd {
        Commands::Select { nodes, key, k } => {
            let nodes: Vec<String> = nodes.split(',').map(str::to_string).collect();
            match rendezvous_hash(&nodes, &key, k) {
                Ok(sel) => println!("{}", sel.join(",")),
                Err(e) => {
                    eprintln!("Error: {}", e);
                    std::process::exit(1);
                }
            }
        }
    }
}
