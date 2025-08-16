// D:\city_chain_project\Algorithm\PoP\pop_rust_src\src\main_pop.rs
//! CLI デモ – GeoJSON を読んで PoP 判定
use anyhow::{Context, Result};
use std::env;

/// ビルド中の bin クレート名は main_pop です。そこから lib.rs（= ライブラリクレート pop_rust）
/// に定義したevents / polygons / types を参照するには pop_rust::… を先頭に付けます
/// （crate:: は bin クレート自身を指すので NG）??
/// bin クレート（main_pop）から同一パッケージのライブラリクレートを参照するときはcrate:: プレフィクスを付ける??
use pop_rust::events::{check_city_event, check_location_event};
use pop_rust::polygons::{load_polygons_from_dir, query_point};
// use pop_rust::types::PolyItem;

fn main() -> Result<()> {
    let dir = env::args()
        .nth(1)
        .unwrap_or_else(|| "polygon_data".into());

    // ────────────────────────────────────
    // (デモ) 指定ディレクトリを読み取り 1 回 load
    // ────────────────────────────────────
    load_polygons_from_dir(&dir).context("load polygons")?;

    let (lat, lon) = (35.02, 139.02);
    println!("Query ({lat}, {lon}) ⇒ {:?}", query_point(lat, lon)?);

    println!("cityA bonus = {}", check_city_event(Some("cityA".into()))?);
    println!(
        "loc bonus   = {}",
        check_location_event(35.015, 139.005)?
    );

    Ok(())
}
