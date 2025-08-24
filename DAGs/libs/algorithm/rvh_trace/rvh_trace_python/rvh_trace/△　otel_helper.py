# \city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_python\rvh_trace\otel_helper.py
"""
otel_helper
===========

ローカル開発時に Docker で簡易 OTLP Collector を起動／停止するユーティリティ。
"""

from __future__ import annotations

import subprocess
import time

import requests


def start_collector(cmd: list[str] | None = None, port: int = 4317, wait: float = 1.0) -> subprocess.Popen[bytes]:
    cmd = cmd or [
        "docker", "run", "--rm", "-d",
        "-p", f"{port}:{port}",
        "--name", "otel-collector",
        "otel/opentelemetry-collector:latest",
    ]
    proc = subprocess.Popen(cmd)
    time.sleep(wait)
    return proc


def stop_collector(proc: subprocess.Popen[bytes]) -> None:
    proc.terminate()
    proc.wait()


def check_collector(endpoint: str = "http://localhost:4317") -> bool:
    try:
        resp = requests.get(endpoint.replace("4317", "4318"))
        return resp.status_code == 200
    except Exception:
        return False
