// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\src\main_faultset.rs
use clap::Parser;
use rvh_faultset_rust::faultset::failover;

#[derive(Parser)]
#[command(name = "faultset", version, about = "Latency-based failover selection")]
struct Cli {
    /// Comma-separated node IDs
    #[arg(long)]
    nodes: String,
    /// Comma-separated latencies (ms)
    #[arg(long)]
    latencies: String,
    /// Threshold latency (ms)
    #[arg(long)]
    threshold: f64,
}

fn main() {
    let cli = Cli::parse();
    let nodes: Vec<String> = cli.nodes.split(',').map(str::to_owned).collect();
    let latencies: Vec<f64> = cli
        .latencies
        .split(',')
        .filter_map(|s| s.parse().ok())
        .collect();

    match failover(&nodes, &latencies, cli.threshold) {
        Ok(selected) => {
            println!("{}", selected.join(","));
            std::process::exit(0);
        }
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
    }
}
