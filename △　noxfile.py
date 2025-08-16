# D:\city_chain_project\noxfile.py
import nox
import os, sys, platform
from pathlib import Path

# 追加 PyO3 cdylib クレートはここに列挙
CRATES = ["bridge_s1", "bridge_s2"]

ROOT = Path(__file__).parent
RUST_DIR = ROOT / "DAGs" / "libs" / "algorithm"       # ★ ここまでで "DAGs"

# 環境変数 CRATES="rvh_trace,poh_holdmetrics" で上書き可能
_crates_env = os.getenv("CRATES")
if _crates_env:
    CRATES = [f"{c.strip()}/{c.strip()}_rust" for c in _crates_env.split(",") if c.strip()]
else:
    CRATES = [
        "rvh_trace/rvh_trace_rust",
        "poh_holdmetrics/poh_holdmetrics_rust",
    ]

def maturin_dev(session, crate: str, target: str | None = None, *, features=None):
    # features は Cargo 側で "python" に統一している前提
    crate_toml = RUST_DIR / crate / "Cargo.toml"
    cmd = ["maturin", "develop", "-m", str(crate_toml), "--release", "--quiet"]
    if features:
        cmd += ["--features", features]
    if target:
        cmd += ["--target", target]
    session.run(*cmd, external=True)

# ---- 環境判定 ----
IS_WINDOWS = sys.platform == "win32"
IS_WSL = "microsoft" in platform.release().lower()
ALLOW_WIN_NATIVE = os.getenv("ALLOW_WINDOWS_NATIVE") == "1"

# Windows ネイティブビルドは基本スキップ（明示した時だけ許可）
def _guard_windows_native(session):
    if IS_WINDOWS and not ALLOW_WIN_NATIVE:
        session.skip("Skip native Windows build (set ALLOW_WINDOWS_NATIVE=1 to force). Use WSL/Container instead.")

# ---------- ① Windows / Rust ----------
@nox.session(python="3.12")
def win_host(session):
    _guard_windows_native(session)
    for c in CRATES:
        maturin_dev(session, c)
    session.run("cargo", "test", "--workspace", external=True)

# ---------- ② Windows / Python ----------
@nox.session(python="3.12")
def win_py(session):
    _guard_windows_native(session)
    for c in CRATES:
        maturin_dev(session, c, features="py-ext")
    # Python ラッパを両方インストール
    session.install("-e", "DAGs/libs/algorithm/rvh_trace/rvh_trace_python[dev]")
    session.install("-e", "DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_python[dev]")
    # 各パッケージのテストを実行
    session.run("pytest",
                "DAGs/libs/algorithm/rvh_trace/rvh_trace_python/rvh_trace/tests",
                "-m", "unit or ffi",
                external=True)
    session.run("pytest",
                "DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_python/poh_holdmetrics/tests",
                "-m", "unit or ffi",
                external=True)

# （任意）Windowsで“ビルドせず”Pythonテストだけしたい時の簡易セッション
@nox.session(python="3.12")
def win_py_prebuilt(session):
    # dist/ または CI artifact から wheel を入れる想定
    wheel_dir = "dist"
    if not Path(wheel_dir).exists():
        session.skip("No prebuilt wheels found (dist/).")
    session.install("--find-links", wheel_dir, "poh_holdmetrics_rust")  # ← prebuilt wheel
    session.install("-e", "DAGs/libs/algorithm/rvh_trace/rvh_trace_python[dev]")
    session.install("-e", "DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_python[dev]")
    session.run("pytest",
                "DAGs/libs/algorithm/rvh_trace/rvh_trace_python/rvh_trace/tests",
                "-m", "unit or ffi",
                external=True)
    session.run("pytest",
                "DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_python/poh_holdmetrics/tests",
                "-m", "unit or ffi",
                external=True)

# ---------- ③ WSL / Rust ----------
@nox.session(python="3.12")
def wsl_rust(session):
    if IS_WINDOWS and not IS_WSL:
        session.skip("Run this inside WSL/Ubuntu")
    for c in CRATES:
        maturin_dev(session, c, target="x86_64-unknown-linux-gnu")
    session.run("cargo", "test", "--workspace", external=True)

# ---------- ④ WSL / Python ----------
@nox.session(python="3.12")
def wsl_py(session):
    if IS_WINDOWS and not IS_WSL:
        session.skip("Run this inside WSL/Ubuntu")
    for c in CRATES:
        maturin_dev(session, c, features="py-ext")
    session.install("-e", "DAGs/libs/algorithm/rvh_trace/rvh_trace_python[dev]")
    session.install("-e", "DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_python[dev]")
    session.run("pytest",
                "DAGs/libs/algorithm/rvh_trace/rvh_trace_python/rvh_trace/tests",
                "-m", "unit or ffi",
                external=True)
    session.run("pytest",
                "DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_python/poh_holdmetrics/tests",
                "-m", "unit or ffi",
                external=True)

# ---------- all-in-one ----------
@nox.session
def all(session):
    # デフォルトは Linux 側だけを回す。Windowsネイティブは手動opt-in。
    for s in ("wsl_rust", "wsl_py"):
        session.notify(s)
