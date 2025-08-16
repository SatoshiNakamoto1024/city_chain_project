// D:\city_chain_project\Algorithm\PoP\pop_rust\tests\test_pop.rs
use std::path::PathBuf;
use pop_rust::polygons::{load_polygons_from_dir, query_point};

/// polygon_data ディレクトリへのフルパスを返します
fn polygon_data_dir() -> PathBuf {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .expect("expected parent of CARGO_MANIFEST_DIR")
        .join("polygon_data")
}

#[test]
fn test_point_in_kanazawa() {
    let dir = polygon_data_dir();
    println!(">>> [test] polygon_data_dir = {:?}", dir);
    load_polygons_from_dir(dir.to_str().unwrap()).unwrap();

    // Kanazawa ポリゴンの明らかに内部にある点
    let latitude = 36.5720;
    let longitude = 136.6460;
    println!(">>> [test] query_point({}, {})", latitude, longitude);
    let result = query_point(latitude, longitude).unwrap();
    println!(">>> [test] result = {:?}", result);
    assert_eq!(
        result,
        Some("kanazawa".to_string()),
        "Point ({},{}) should be inside kanazawa",
        latitude,
        longitude
    );
}

#[test]
fn test_point_in_paris() {
    let dir = polygon_data_dir();
    println!(">>> [test] polygon_data_dir = {:?}", dir);
    load_polygons_from_dir(dir.to_str().unwrap()).unwrap();

    // Paris ポリゴンの明らかに内部にある点
    let latitude = 48.8600;
    let longitude = 2.3370;
    println!(">>> [test] query_point({}, {})", latitude, longitude);
    let result = query_point(latitude, longitude).unwrap();
    println!(">>> [test] result = {:?}", result);
    assert_eq!(
        result,
        Some("paris".to_string()),
        "Point ({},{}) should be inside paris",
        latitude,
        longitude
    );
}

#[test]
fn test_point_outside_all() {
    let dir = polygon_data_dir();
    println!(">>> [test] polygon_data_dir = {:?}", dir);
    load_polygons_from_dir(dir.to_str().unwrap()).unwrap();

    // どのポリゴンにも含まれない点
    let latitude = 0.0;
    let longitude = 0.0;
    println!(">>> [test] query_point({}, {})", latitude, longitude);
    let result = query_point(latitude, longitude).unwrap();
    println!(">>> [test] result = {:?}", result);
    assert!(
        result.is_none(),
        "Point ({},{}) should be outside all polygons",
        latitude,
        longitude
    );
}
