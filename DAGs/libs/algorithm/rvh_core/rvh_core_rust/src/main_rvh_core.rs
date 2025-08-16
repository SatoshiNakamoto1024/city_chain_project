// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\src\main_rvh_core.rs
// CLI ― Rendezvous-Hash を試す小さなツール
//
/// 例:
/// ```bash
/// cargo run --bin rvh -- select \
///     --nodes alpha,beta,gamma --key file-42 --k 2
/// ```
use clap::{Parser, Subcommand};
use rvh_core_rust::rendezvous::rendezvous_hash;

/// コマンドライン定義
#[derive(Parser)]
#[command(name = "rvh", version, about = "Rendezvous-Hash CLI")]
struct Cli {
    #[command(subcommand)]
    cmd: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// ノード一覧から k 個を選択
    Select {
        /// `node1,node2,...` 形式
        #[arg(long)]
        nodes: String,
        /// ハッシュキー（オブジェクト ID など）
        #[arg(long)]
        key: String,
        /// 取り出す個数
        #[arg(long)]
        k: usize,
    },
}

fn main() {
    let cli = Cli::parse();
    match cli.cmd {
        Commands::Select { nodes, key, k } => {
            let nodes: Vec<String> = nodes.split(',').map(str::to_owned).collect();

            match rendezvous_hash(&nodes, &key, k) {
                Ok(sel) => {
                    println!("{}", sel.join(","));
                }

                // --------------------------------------------------
                // non-exhaustive 型なので「その他すべて」を受ける分岐を必ず入れる
                // --------------------------------------------------
                Err(e) => {
                    // 既知バリアント: NoNodes / TooMany … いずれもここで拾える
                    eprintln!("Error: {e}");
                    std::process::exit(1);
                }
            }
        }
    }
}
