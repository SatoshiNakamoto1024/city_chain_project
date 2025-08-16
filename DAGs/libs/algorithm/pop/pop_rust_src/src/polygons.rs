// D:\city_chain_project\Algorithm\PoP\pop_rust_src\src\polygons.rs
use pyo3::prelude::*;
use std::{fs, path::Path, sync::Mutex};

use once_cell::sync::Lazy;
use geo::{algorithm::{bounding_rect::BoundingRect, contains::Contains}, Coord, Point, Polygon, LineString};
use geo::EuclideanDistance;
use rstar::{PointDistance, RTree, RTreeObject, AABB};
use geojson::{GeoJson, Value};

use crate::types::PolyItem;

/// ─────────── RTree ノード
#[derive(Clone)]
struct PolyNode {
    city: String,
    poly: Polygon<f64>,
    bbox: AABB<[f64; 2]>,
}
impl RTreeObject for PolyNode {
    type Envelope = AABB<[f64; 2]>;
    fn envelope(&self) -> Self::Envelope { self.bbox }
}
impl PointDistance for PolyNode {
    fn distance_2(&self, p: &[f64; 2]) -> f64 {
        self.poly.euclidean_distance(&Point::new(p[0], p[1])).powi(2)
    }
}

static TREE: Lazy<Mutex<Option<RTree<PolyNode>>>> = Lazy::new(|| Mutex::new(None));

/// `.geojson` を全部読んで RTree にロード
#[pyfunction]
pub fn load_polygons_from_dir(dir: &str) -> PyResult<()> {
    let mut items = Vec::<PolyItem>::new();
    println!(">>> [load] Loading polygons from directory: {}", dir);

    for entry in fs::read_dir(Path::new(dir))
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyOSError, _>(e.to_string()))?
    {
        let p = entry?.path();
        println!(">>> [load] Checking file: {:?}", p);
        if p.extension().and_then(|s| s.to_str()) != Some("geojson") {
            println!(">>> [load] Skipping non-geojson file");
            continue;
        }

        let text = fs::read_to_string(&p)?;
        let gj: GeoJson = text
            .parse()
            .map_err(|e: geojson::Error| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        if let GeoJson::FeatureCollection(fc) = gj {
            for f in fc.features {
                let Some(geometry) = f.geometry.as_ref() else {
                    println!(">>> [load] feature.geometry is None, skip");
                    continue;
                };
                let Value::Polygon(ref coords) = &geometry.value else {
                    println!(">>> [load] geometry.value is not Polygon, skip");
                    continue;
                };
                let city_id = f.properties
                    .as_ref()
                    .and_then(|m| m.get("name"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("unknown")
                    .to_string();

                // GeoJSON は [lon, lat] のタプル
                let flat: Vec<(f64, f64)> = coords[0]
                    .iter()
                    .map(|pos| {
                        let lon = pos[0];
                        let lat = pos[1];
                        println!(">>> [load] raw coord [lon,lat]=[{:.6},{:.6}]", lon, lat);
                        (lon, lat)
                    })
                    .collect();
                println!(">>> [load] Loaded polygon: {} ({} points)", city_id, flat.len());
                items.push(PolyItem { city_id, coords: flat });
            }
        } else {
            println!(">>> [load] geojson is not FeatureCollection, skip");
        }
    }

    println!(">>> [load] Total polygons found: {}", items.len());

    // PolyItem → RTree ノード
    let nodes: Vec<_> = items.into_iter().map(|it| {
        // it.coords は (lon, lat) のタプル
        let ring: LineString<f64> = it.coords.iter()
            .map(|(lon, lat)| {
                println!(">>> [build] Building ring coord: lon={}, lat={}", lon, lat);
                Coord { x: *lon, y: *lat }
            })
            .collect::<Vec<_>>()
            .into();
        let poly = Polygon::new(ring.clone(), vec![]);
        println!(">>> [build] Polygon for '{}' bounding_rect: {:?}", it.city_id, poly.bounding_rect());
        let rect = poly.bounding_rect().unwrap();
        let bbox = AABB::from_corners([rect.min().x, rect.min().y], [rect.max().x, rect.max().y]);
        PolyNode { city: it.city_id, poly, bbox }
    }).collect();

    println!(">>> [load] Inserting {} nodes into RTree", nodes.len());
    *TREE.lock().unwrap() = Some(RTree::bulk_load(nodes));
    println!(">>> [load] RTree ready");
    Ok(())
}

/// 点が属する city_id を返す
#[pyfunction]
pub fn query_point(lat: f64, lon: f64) -> PyResult<Option<String>> {
    let guard = TREE.lock().unwrap();
    let tree = guard.as_ref().ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("RTree not ready")
    })?;

    // DEBUG only
    #[cfg(debug_assertions)]
    println!("[query] lat={}, lon={}", lat, lon);

    let pt = Point::new(lon, lat);

    // -- production: use intersecting search --
    for node in tree.locate_in_envelope_intersecting(&AABB::from_point([lon, lat])) {
        if node.poly.contains(&pt) {
            return Ok(Some(node.city.clone()));
        }
    }

    // -- fallback eps-box if needed --
    // let eps = 1e-9;
    // let aabb = AABB::from_corners([lon-eps,lat-eps], [lon+eps,lat+eps]);
    // for node in tree.locate_in_envelope(&aabb) {
    //     if node.poly.contains(&pt) {
    //         return Ok(Some(node.city.clone()));
    //     }
    // }

    Ok(None)
}
