// D:\city_chain_project\Algorithm\PoP\pop_rust\src\bin\main_pop.rs
use anyhow::Context;
use std::env;
use std::fs;

use pop_rust::types::PolyItem;
use pop_rust::polygons::{load_polygons_from_dir, query_point};
use pop_rust::events::{check_city_event, check_location_event};

fn main() -> anyhow::Result<()> {
    // polygon_data ディレクトリ（第一引数）またはデフォルト
    let dir = env::args()
        .nth(1)
        .unwrap_or_else(|| "polygon_data".to_string());

    let mut items: Vec<PolyItem> = Vec::new();

    for entry in fs::read_dir(&dir).context("reading polygon_data directory")? {
        let entry = entry.context("dir entry")?;
        let text  = fs::read_to_string(entry.path()).context("reading geojson file")?;
        let gj: geojson::GeoJson = text.parse().context("parsing geojson")?;
        if let geojson::GeoJson::FeatureCollection(fc) = gj {
            for feature in fc.features {
                if let Some(geom) = feature.geometry {
                    if let geojson::Value::Polygon(coords) = geom.value {
                        // プロパティ "name" を city_id に使う
                        let city_id = feature.properties
                            .as_ref()
                            .and_then(|m| m.get("name"))
                            .and_then(|v| v.as_str())
                            .unwrap_or("unknown")
                            .to_string();
                        // coords の第一リングを取り出し、Vec<Vec<f64>>
                        let flat = coords[0]
                            .iter()
                            // Vec<f64> の [lon,lat] を (lat,lon) に直す
                            .map(|pt| (pt[1], pt[0]))
                            .collect::<Vec<_>>();
                        items.push(PolyItem { city_id, coords: flat });
                    }
                }
            }
        }
    }

    // RTree 構築
    load_polygons_from_dir(&dir).context("failed to load polygons")?;
    println!("[main_pop] loaded polygons from `{}`", dir);

    // Query テスト
    let pt = (35.02, 139.02);
    match query_point(pt.0, pt.1)? {
        Some(city) => println!("[main_pop] Point {:?} in {}", pt, city),
        None       => println!("[main_pop] Point {:?} not in any city", pt),
    }

    // イベント倍率テスト
    let cm = check_city_event(Some("cityA".to_string()))?;
    println!("[main_pop] cityA multiplier = {}", cm);
    let lm = check_location_event(35.015, 139.005)?;
    println!("[main_pop] location multiplier = {}", lm);

    Ok(())
}
