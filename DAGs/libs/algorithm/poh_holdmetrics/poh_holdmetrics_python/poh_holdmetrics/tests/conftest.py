# \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\conftest.py
# (tests ディレクトリ直下)

import os
import sys
import time
import socket
import subprocess
import pytest

# --- ランタイム前提（手動起動で必要だった環境変数をテスト実行プロセスにも適用） ---
os.environ.setdefault("POH_DISABLE_RUST", "1")
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION", "3")

# 利用可能なポートを確保
def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()

@pytest.fixture(scope="session")
def grpc_address() -> str:
    return f"127.0.0.1:{_free_port()}"

@pytest.fixture(scope="session", autouse=True)
def _grpc_server(grpc_address: str):
    """
    pytest 開始時に gRPC サーバをサブプロセスで起動し、
    全テスト終了後に terminate する。
    """
    env = os.environ.copy()
    env["GRPC_ADDRESS"] = grpc_address

    # venv の Python を確実に使う
    cmd = [sys.executable, "-m", "poh_holdmetrics.app_holdmetrics", "grpc"]

    # ログを取りつつ起動
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # 行バッファ
    )

    # 起動待ち（ログ or ポート LISTEN で判定）
    deadline = time.time() + 30  # Windows は起動が遅いことがあるので余裕を持つ
    logs: list[str] = []
    host, port_s = grpc_address.split(":")
    port = int(port_s)

    started = False
    while time.time() < deadline:
        # プロセスが早期終了していないかを先に確認
        if proc.poll() is not None:
            # 既に終了している → ログを吸い出してエラーにする
            try:
                if proc.stdout:
                    logs.extend(proc.stdout.readlines())
            except Exception:
                pass
            raise RuntimeError(
                f"gRPC server exited immediately with code {proc.returncode}\n"
                + "".join(logs[-200:])
            )

        # 1 行だけ非ブロッキング読み取り（行が来たら保存）
        try:
            if proc.stdout:
                line = proc.stdout.readline()
                if line:
                    logs.append(line)
                    # サーバ側ログの決め台詞
                    if "gRPC server started" in line:
                        started = True
                        break
        except Exception:
            pass

        # ポートが開いたら OK
        try:
            with socket.create_connection((host, port), timeout=0.3):
                started = True
                break
        except OSError:
            time.sleep(0.2)

    if not started:
        # 片付けて詳細ログ付きで失敗
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        raise RuntimeError(
            "gRPC server did not start in time.\n" + "".join(logs[-200:])
        )

    # ---- テスト実行 ----
    try:
        yield
    finally:
        # 後始末
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception:
            pass
