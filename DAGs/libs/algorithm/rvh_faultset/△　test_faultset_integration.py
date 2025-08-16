# D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\test_faultset_integration.py
#!/usr/bin/env python3
# D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\test_faultset_integration.py

"""
Integration test for the end-to-end rvh_faultset pipeline:

  1. Pure-Python Geohash clustering
  2. Rust 実装の failover() 呼び出し
  3. 最終結果のマージ＆検証

使い方:
    python test_faultset_integration.py
    or
    pytest -v test_faultset_integration.py
"""

import sys
import pathlib
import pytest

# ── テスト対象のパッケージを優先ロード ──
ROOT = pathlib.Path(__file__).parent

# Rust バックエンド（bindings.rs の #[pymodule] 名が rvh_faultset）
sys.path.insert(0, str(ROOT / "rvh_faultset_rust" / "target" / "wheels"))
# Python ラッパー
sys.path.insert(0, str(ROOT / "rvh_faultset_python"))

from rvh_faultset import faultset, FaultsetError
import rvh_faultset  # Rust モジュールとしてこれをimportします

# テスト用のノード一覧
BASE_NODES = [
    {"id": "a", "lat": 35.0, "lon": 139.0, "latency":  50.0},
    {"id": "b", "lat": 51.5, "lon":  -0.1, "latency": 200.0},
    {"id": "c", "lat": 40.7, "lon":  -74.0, "latency":  75.0},
    {"id": "d", "lat": 35.0, "lon": 140.0, "latency": 150.0},
]

def test_end_to_end_basic():
    """
    threshold=100.0, precision=5 のとき、
    geohash が同じクラスタに入る a と c が survivors に含まれること。
    """
    survivors = faultset(BASE_NODES, threshold=100.0, precision=5)
    assert isinstance(survivors, list)
    assert set(survivors) == {"a", "c"}

def test_end_to_end_empty_input():
    """空リスト入力で即座に FaultsetError を返すこと"""
    with pytest.raises(FaultsetError):
        faultset([], threshold=50.0, precision=6)

def test_end_to_end_all_filtered_out():
    """
    precision を高めて各ノードが別クラスタになるようにし、
    いずれのクラスタも survivors が空になる場合に FaultsetError。
    """
    nodes = [
        {"id": "x", "lat":  0.0, "lon":   0.0, "latency": 250.0},
        {"id": "y", "lat":  1.0, "lon":   1.0, "latency": 260.0},
    ]
    with pytest.raises(FaultsetError):
        faultset(nodes, threshold=100.0, precision=12)

if __name__ == "__main__":
    # このスクリプト単体実行対応
    sys.exit(pytest.main([__file__]))
