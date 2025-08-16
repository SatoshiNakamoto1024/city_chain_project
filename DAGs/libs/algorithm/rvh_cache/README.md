rvh_cache	LRU／ARC キャッシュ + TTL。rvh_core が計算した HRW 結果をメモ化し 10× スループット	1	
@lru_cache(maxsize=50_000), get_hrw_for_tx(tx_id, candidates)