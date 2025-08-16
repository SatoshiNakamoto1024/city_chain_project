// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\cli.rs
use clap::{Parser, Subcommand};
use crate::sharding;
use crate::metrics;

#[derive(Parser)]
#[command(name = "ec_rust", about = "Erasure Coding CLI")]
struct Cli {
    #[command(subcommand)]
    cmd: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Encode an input file into shards
    Encode {
        /// Path to the input file
        #[arg(short, long)]
        input: String,
        /// Directory to write shards into
        #[arg(short, long)]
        output: String,
        /// Number of data shards
        #[arg(long, default_value_t = 4)]
        data_shards: usize,
        /// Number of parity shards
        #[arg(long, default_value_t = 2)]
        parity_shards: usize,
    },
    /// Decode shards back into the original file
    Decode {
        /// Directory containing shard files (.bin)
        #[arg(short, long)]
        input: String,
        /// Path to write the recovered file
        #[arg(short, long)]
        output: String,
        /// Number of data shards
        #[arg(long, default_value_t = 4)]
        data_shards: usize,
        /// Number of parity shards
        #[arg(long, default_value_t = 2)]
        parity_shards: usize,
    },
    /// Show encode/decode timing metrics
    Status,
}

fn run() -> anyhow::Result<()> {
    let cli = Cli::parse();
    match cli.cmd {
        Commands::Encode { input, output, data_shards, parity_shards } => {
            let data = std::fs::read(&input)?;
            let shards = sharding::encode_shards(&data, data_shards, parity_shards)?;
            std::fs::create_dir_all(&output)?;
            for (i, shard) in shards.into_iter().enumerate() {
                let path = format!("{}/shard{}.bin", &output, i);
                std::fs::write(path, shard)?;
            }
            println!("Encoded {} data shards and {} parity shards into `{}`",
                     data_shards, parity_shards, output);
        }
        Commands::Decode { input, output, data_shards, parity_shards } => {
            let mut shards_opt = Vec::new();
            for entry in std::fs::read_dir(&input)? {
                let path = entry?.path();
                if path.extension().and_then(|s| s.to_str()) == Some("bin") {
                    shards_opt.push(Some(std::fs::read(path)?));
                }
            }
            let data = sharding::decode_shards(shards_opt, data_shards, parity_shards)?;
            std::fs::write(&output, &data)?;
            println!("Decoded original data to `{}`", output);
        }
        Commands::Status => {
            let enc = metrics::get_encode_time();
            let dec = metrics::get_decode_time();
            println!("encode_time_ns: {}, decode_time_ns: {}", enc, dec);
        }
    }
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }
}
