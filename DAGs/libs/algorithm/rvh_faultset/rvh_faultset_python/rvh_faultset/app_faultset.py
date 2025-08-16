# D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python\rvh_faultset\app_faultset.py

"""
CLI サンプル:

# 同期版
python -m rvh_faultset.app_faultset \
    -n n1:35.0:139.0:50,n2:51.5:-0.1:200,n3:40.7:-74.0:75 \
    -t 100.0 -p 5

# 非同期版
python -m rvh_faultset.app_faultset \
    -n n1:35.0:139.0:50,n2:51.5:-0.1:200,n3:40.7:-74.0:75 \
    -t 100.0 -p 5 --async

# --level は互換用で受け取るだけ
python -m rvh_faultset.app_faultset \
    -n a:35.0:139.0:50,b:51.5:-0.1:200,c:40.7:-74.0:75 \
    -t 100.0 -p 5 --level debug
"""

import argparse
import sys
import asyncio

from .faultset_builder import faultset, faultset_async, FaultsetError


def parse_nodes(spec: str):
    """
    "id:lat:lon:latency,..." 形式の文字列を解析して dict のリストを返す。
    """
    out = []
    for part in spec.split(","):
        try:
            nid, lat, lon, latn = part.split(":")
            out.append({
                "id": nid,
                "lat": float(lat),
                "lon": float(lon),
                "latency": float(latn),
            })
        except ValueError:
            raise ValueError(f"invalid node spec: {part!r}")
    return out


def main():
    parser = argparse.ArgumentParser(
        prog="app_faultset",
        description="Geohash + Rust failover CLI (sync/async)")
    parser.add_argument(
        "-n", "--nodes", required=True,
        help="id:lat:lon:latency をカンマ区切りで指定")
    parser.add_argument(
        "-t", "--threshold", type=float, required=True,
        help="latency threshold (ms)")
    parser.add_argument(
        "-p", "--precision", type=int, default=6,
        help="geohash precision (1–12)")
    parser.add_argument(
        "-a", "--async", dest="use_async",
        action="store_true",
        help="非同期版 faultset_async() を使う")
    parser.add_argument(
        "--level", default=None,
        help="互換用。ログレベルなど自由に受け取るだけ")
    args = parser.parse_args()

    # --level は今は使わないが、互換性確保のために受け取る
    if args.level:
        # 必要なら logging レベル設定などに使う
        pass

    try:
        nodes = parse_nodes(args.nodes)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.use_async:
            # 非同期版を asyncio.run で実行
            survivors = asyncio.run(
                faultset_async(nodes, args.threshold, args.precision)
            )
        else:
            # 同期版
            survivors = faultset(nodes, args.threshold, args.precision)
        print("Survivors:", survivors)
    except FaultsetError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
