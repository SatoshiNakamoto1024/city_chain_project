// D:\city_chain_project\Algorithm\PoP\pop_rust_src\src\events.rs
use pyo3::prelude::*;
use std::time::{SystemTime, UNIX_EPOCH};
use geo::Point;
use geo::algorithm::contains::Contains;

/// City ボーナスイベント倍率を返す
#[pyfunction]
pub fn check_city_event(city_id: Option<String>) -> PyResult<f64> {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyOSError, _>(format!("{:?}", e)))?
        .as_secs();

    let events = vec![
        ("cityA".to_string(), 1672531200, 1672534800, 3.0),
        ("cityB".to_string(), 1672531200, u64::MAX, 2.0),
    ];

    if let Some(id) = city_id {
        for (cid, start, end, mult) in events {
            if id == cid && start <= now && now <= end {
                return Ok(mult);
            }
        }
    }
    Ok(1.0)
}

/// 位置ボーナスイベント倍率を返す
#[pyfunction]
pub fn check_location_event(lat: f64, lon: f64) -> PyResult<f64> {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyOSError, _>(format!("{:?}", e)))?
        .as_secs();

    // デモ用ポリゴン＋イベント範囲
    let polys = vec![
        (
            vec![(35.01, 139.0), (35.02, 139.0), (35.02, 139.01), (35.01, 139.01)],
            1672531200,
            1672534800,
            5.0,
        ),
    ];

    let pt = Point::new(lon, lat);
    for (coords, start, end, mult) in polys {
        if start <= now && now <= end {
            let ring = coords.iter()
                .map(|(lt, ln)| geo::Coord { x: *ln, y: *lt })
                .collect::<Vec<_>>()
                .into();
            let poly = geo::Polygon::new(ring, vec![]);
            if poly.contains(&pt) {
                return Ok(mult);
            }
        }
    }
    Ok(1.0)
}
