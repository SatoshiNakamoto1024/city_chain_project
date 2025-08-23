pop_geo	GeoJSON 読み込み→geo Polygon 化  R‑tree (rstar) 構築 / point‑in‑polygon 判定	2
fn build_index(dir:&Path)->GeoIndex,impl GeoIndex { fn query(&self, p:Point)->Option<CityId> }
