# D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python\rvh_faultset\app_faultset.py
# rvh_faultset_python/rvh_faultset/app_faultset.py

"""
CLI サンプル:

$ python -m rvh_faultset.app_faultset \
    --nodes "a:35.0:139.0:50,b:51.5:-0.1:200" \
    --threshold 100.0 \
    --precision 5
"""

import argparse
import sys
from .faultset_builder import faultset, FaultsetError

def main():
    parser = argparse.ArgumentParser(prog="app_faultset",
                                     description="Geohash + Rust failover CLI")
    parser.add_argument("-n", "--nodes", required=True,
                        help="id:lat:lon:latency をカンマ区切り")
    parser.add_argument("-t", "--threshold", type=float, required=True,
                        help="latency threshold")
    parser.add_argument("-p", "--precision", type=int, default=5,
                        help="geohash precision (1–12)")
    args = parser.parse_args()

    # 文字列 → dict リスト
    nodes = []
    for part in args.nodes.split(","):
        try:
            nid, lat, lon, latn = part.split(":")
            nodes.append({
                "id": nid,
                "lat": float(lat),
                "lon": float(lon),
                "latency": float(latn),
            })
        except ValueError:
            print(f"invalid node spec: {part}", file=sys.stderr)
            sys.exit(1)

    try:
        survivors = faultset(nodes, args.threshold, args.precision)
        print("Survivors:", survivors)
    except FaultsetError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
