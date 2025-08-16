// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\main_pipeline.rs
// -------------------------------------------------------------
//   ldpc-pipeline CLI
//     $ cargo run -p ldpc-pipeline --bin main_pipeline -- send \
//           --file ./big.iso --to 127.0.0.1:4000 --tier city
//
//     $ cargo run -p ldpc-pipeline --bin main_pipeline -- recv \
//           --out ./big.iso --listen 0.0.0.0:4000
// -------------------------------------------------------------
use std::{net::SocketAddr, path::PathBuf};

use anyhow::Result;
use clap::{Parser, Subcommand};
use futures::StreamExt;
use tokio::{
    fs::File,
    io::{AsyncWriteExt, BufReader, BufWriter},
    net::{TcpListener, TcpStream},
    sync::mpsc,
};

use ldpc::{
    decode_stream, encode_stream,
    receiver::tcp as tcp_receiver,
    sender::tcp as tcp_sender,
    Tier,
};

/// ---- ldpc_core（行列・エンコーダ） -------------------------
use ldpc_core::{
    decoder::peeling::PeelingDecoder,
    encoder::LDPCEncoder,
    design::qcpeg::SparseMatrix,
    tiers::{CITY, CONTINENT, GLOBAL},
};

/// ================================ CLI 定義 ================================
#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// ファイルを読み込みながら LDPC シャーディング → TCP 送信
    Send {
        /// 送信する元ファイル
        #[arg(short, long)]
        file: PathBuf,
        /// 接続先アドレス (例: 127.0.0.1:4000)
        #[arg(short, long)]
        to: SocketAddr,
        /// city / continent / global
        #[arg(short, long, default_value = "city")]
        tier: String,
    },
    /// TCP でシャード受信 → 復号してファイル出力
    Recv {
        /// 出力ファイル
        #[arg(short, long)]
        out: PathBuf,
        /// 待ち受けアドレス
        #[arg(short, long)]
        listen: SocketAddr,
    },
}

/// 文字列 tier → (Tier enum, cfg, seed)
fn tier_from(s: &str) -> (Tier, ldpc_core::design::qcpeg::QcPegConfig, u64) {
    match s.to_ascii_lowercase().as_str() {
        "city" => (Tier::City, CITY, 0xC17),
        "continent" => (Tier::Continent, CONTINENT, 0xC0NT1),
        "global" => (Tier::Global, GLOBAL, 0xG10B4),
        _ => {
            eprintln!("Unknown tier `{s}`, fallback to city");
            (Tier::City, CITY, 0xC17)
        }
    }
}

/// ================================ main ================================
#[tokio::main(flavor = "multi_thread")]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter("info")
        .init();

    match Cli::parse().cmd {
        //=================================================================
        // 送信側
        //=================================================================
        Cmd::Send { file, to, tier } => {
            // --- プレーンファイルを非同期で開く
            let in_file = File::open(&file).await?;
            let reader = BufReader::new(in_file);

            // --- tier から行列プリセット
            let (tier_enum, cfg, seed) = tier_from(&tier);
            let encoder = LDPCEncoder::new(cfg, seed);

            // --- TCP 接続
            let socket = TcpStream::connect(to).await?;
            let (mut framed_sink, _stream) = tcp_sender::framed(socket);

            // --- シャードを中継するチャンネル
            let (pkt_tx, mut pkt_rx) = mpsc::channel(1024);

            // --- encode → pkt_tx
            let enc_task = encode_stream(reader, encoder, tier_enum, pkt_tx);

            // --- チャンネル → ソケット
            let net_task = tokio::spawn(async move {
                while let Some(pkt) = pkt_rx.recv().await {
                    framed_sink.send(pkt).await?;
                }
                Ok::<(), anyhow::Error>(())
            });

            tokio::try_join!(enc_task, net_task)?;
        }

        //=================================================================
        // 受信側
        //=================================================================
        Cmd::Recv { out, listen } => {
            let listener = TcpListener::bind(listen).await?;
            let (socket, _) = listener.accept().await?;

            let (_sink, mut framed_stream) = tcp_receiver::framed(socket);

            let writer = BufWriter::new(File::create(&out).await?);

            // --- TCP → ch
            let (pkt_tx, pkt_rx) = mpsc::channel(1024);
            let sock_task = tokio::spawn(async move {
                while let Some(pkt) = framed_stream.next().await {
                    pkt_tx.send(pkt?).await.ok();
                }
                Ok::<(), anyhow::Error>(())
            });

            // --- きわめて単純な PeelingDecoder (行列はパケット情報から再取得する想定)
            //     ここではダミー行列で初期化
            let dummy_h = SparseMatrix::default();
            let decoder = PeelingDecoder::new(dummy_h, 0, 0);

            let dec_task = decode_stream(pkt_rx, decoder, writer);

            tokio::try_join!(sock_task, dec_task)?;
        }
    }

    Ok(())
}
