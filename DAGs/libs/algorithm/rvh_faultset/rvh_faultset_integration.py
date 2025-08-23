# D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_integration.py

"""
Integration test for the end-to-end rvh_faultset pipeline, sync & async:

  1. Pure-Python Geohash clustering
  2. Rust failover() 呼び出し
  3. 最終マージ＆検証
  4. CLI 連携 (sync + --async)

Use:
    python rvh_faultset_integration.py
    pytest -v rvh_faultset_integration.py
"""

import sys
import pathlib
import pytest
import subprocess

ROOT = pathlib.Path(__file__).parent

# make sure we load our built Rust wheel first
sys.path.insert(0, str(ROOT / "rvh_faultset_rust" / "target" / "wheels"))
# then our Python package
sys.path.insert(0, str(ROOT / "rvh_faultset_python"))

from rvh_faultset import faultset, faultset_async, FaultsetError

BASE_NODES = [
    {"id": "a", "lat": 35.0, "lon": 139.0, "latency":  50.0},
    {"id": "b", "lat": 51.5, "lon": -0.1, "latency": 200.0},
    {"id": "c", "lat": 40.7, "lon": -74.0, "latency":  75.0},
    {"id": "d", "lat": 35.0, "lon": 140.0, "latency": 150.0},
]


def test_sync_basic():
    """sync: threshold=100, precision=5 なら a,c が残る"""
    survivors = faultset(BASE_NODES, threshold=100.0, precision=5)
    assert isinstance(survivors, list)
    assert set(survivors) == {"a", "c"}


@pytest.mark.asyncio
async def test_async_basic():
    """async: 同上を await で呼び出せる"""
    survivors = await faultset_async(BASE_NODES, threshold=100.0, precision=5)
    assert isinstance(survivors, list)
    assert set(survivors) == {"a", "c"}


def test_sync_empty():
    """sync: 空入力で FaultsetError"""
    with pytest.raises(FaultsetError):
        faultset([], threshold=50.0, precision=6)


@pytest.mark.asyncio
async def test_async_empty():
    """async: 同上を await で呼び出すと FaultsetError"""
    with pytest.raises(FaultsetError):
        await faultset_async([], threshold=50.0, precision=6)


def test_sync_all_filtered():
    """sync: precision=12 で分散クラスタ → 全フィルタアウト → エラー"""
    nodes = [
        {"id": "x", "lat":  0.0, "lon":   0.0, "latency": 250.0},
        {"id": "y", "lat":  1.0, "lon":   1.0, "latency": 260.0},
    ]
    with pytest.raises(FaultsetError):
        faultset(nodes, threshold=100.0, precision=12)


@pytest.mark.asyncio
async def test_async_all_filtered():
    """async: 同上を await"""
    nodes = [
        {"id": "x", "lat":  0.0, "lon":   0.0, "latency": 250.0},
        {"id": "y", "lat":  1.0, "lon":   1.0, "latency": 260.0},
    ]
    with pytest.raises(FaultsetError):
        await faultset_async(nodes, threshold=100.0, precision=12)


def test_cli_sync(tmp_path):
    """CLI sync モード (-p precision)"""
    cmd = [
        sys.executable, "-m", "rvh_faultset.app_faultset",
        "--nodes", "a:35.0:139.0:50,b:51.5:-0.1:200,c:40.7:-74.0:75",
        "--threshold", "100.0",
        "--precision", "5",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    # 出力例: "Survivors: ['a', 'c']\n"
    assert "a" in res.stdout and "c" in res.stdout


def test_cli_async(tmp_path):
    """CLI async モード (--async)"""
    cmd = [
        sys.executable, "-m", "rvh_faultset.app_faultset",
        "--nodes", "a:35.0:139.0:50,b:51.5:-0.1:200,c:40.7:-74.0:75",
        "--threshold", "100.0",
        "--precision", "5",
        "--async",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "a" in res.stdout and "c" in res.stdout


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
