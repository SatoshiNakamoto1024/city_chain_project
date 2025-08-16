// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\main_ec.rs
use clap::{Parser, Subcommand};
use reed_solomon_erasure::galois_8::ReedSolomon;
use std::error::Error;
use std::fs;
use std::io::{Read, Write};
use std::path::PathBuf;

/// Standalone RS CLI (alternative interface)
#[derive(Parser)]
#[command(name = "main_ec", about = "Reed–Solomon Erasure Coding CLI")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Encode a file into n shards (k required to recover)
    Encode {
        #[arg(short, long)]
        input: PathBuf,
        #[arg(short, long)]
        n: usize,
        #[arg(short, long)]
        k: usize,
        #[arg(short, long)]
        output: PathBuf,
    },
    /// Decode shards back into file
    Decode {
        #[arg(short = 'd', long = "shards-dir")]
        shards_dir: PathBuf,
        #[arg(short, long)]
        k: usize,
        #[arg(short, long)]
        output: PathBuf,
    },
}

fn main() -> Result<(), Box<dyn Error>> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Encode { input, n, k, output } => {
            let mut data = Vec::new();
            fs::File::open(&input)?.read_to_end(&mut data)?;
            let parity = n.saturating_sub(k);
            let rs = ReedSolomon::new(k, parity)?;
            let mut shards = rs.split(&data)?;
            rs.encode(&mut shards)?;
            fs::create_dir_all(&output)?;
            for (i, shard) in shards.into_iter().enumerate() {
                let mut path = output.clone();
                path.push(format!("shard{}.dat", i));
                fs::File::create(&path)?.write_all(&shard)?;
            }
            println!("Wrote {} shards to {:?}", n, output);
        }
        Commands::Decode { shards_dir, k, output } => {
            let mut shards = Vec::new();
            for entry in fs::read_dir(&shards_dir)? {
                let path = entry?.path();
                if path.extension().and_then(|s| s.to_str()) == Some("dat") {
                    let mut buf = Vec::new();
                    fs::File::open(&path)?.read_to_end(&mut buf)?;
                    shards.push(Some(buf));
                }
            }
            let total = shards.len();
            let parity = total.saturating_sub(k);
            let rs = ReedSolomon::new(k, parity)?;
            let mut shards = shards;
            rs.reconstruct(&mut shards)?;
            let data = rs.join_data(&shards)?;
            fs::File::create(&output)?.write_all(&data)?;
            println!("Recovered data written to {:?}", output);
        }
    }
    Ok(())
}
