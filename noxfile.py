# \city_chain_project\noxfile.py
# noxfile.py
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import nox

ROOT = Path(__file__).parent
RUST_DIR = ROOT / "DAGs" / "libs" / "algorithm"
SERVICES_YAML = ROOT / "services.yaml"

try:
    import yaml  # type: ignore
except Exception as e:
    print("[nox] PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    raise

def load_cfg() -> Dict[str, Any]:
    if not SERVICES_YAML.exists():
        raise FileNotFoundError(f"{SERVICES_YAML} not found")
    with SERVICES_YAML.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def crate_root_from_crate_path(crate_path: str) -> Path:
    p = Path(crate_path)
    return p.parent if p.name.endswith("_rust") else p

def maturin_develop(session: nox.Session, crate_toml: Path, features: List[str] | None) -> None:
    cmd = ["maturin", "develop", "-m", str(crate_toml), "--release", "--quiet"]
    if features:
        cmd += ["--features", ",".join(features)]
    session.run(*cmd, external=True)

# ---- セッション ------------------------------------------------------------

@nox.session(python="3.12")
def py(session: nox.Session) -> None:
    """
    services.yaml の pyext を:
      1) maturin develop（Rust拡張ビルド）
      2) Python ラッパを -e で入れる
      3) テスト（pytest）を実行
    """
    cfg = load_cfg()
    pyexts = cfg.get("pyext", []) or []

    # まず必要ツール
    session.install("maturin==1.5.1", "pytest>=8,<9")

    for px in pyexts:
        kind = px.get("kind", "mixed")
        if kind not in ("mixed", "python"):
            # Rustのみは対象外
            continue

        crate_path = px["crate_path"]
        crate_root = crate_root_from_crate_path(crate_path)
        rust_dir = crate_root / f"{crate_root.name}_rust"
        rust_toml = rust_dir / "Cargo.toml"

        wrapper = px.get("python_wrapper")
        features = px.get("features") or ["python"]

        # 1) Rust拡張があれば maturin develop
        if rust_toml.exists() and kind == "mixed":
            maturin_develop(session, rust_toml, features=features)

        # 2) Python ラッパを入れる（あれば）
        if wrapper:
            session.install("-e", f"{wrapper}[dev]")

        # 3) テスト
        for t in px.get("tests", []) or []:
            if t.get("kind") == "pytest":
                args = ["-q", t["path"]]
                if t.get("markers"):
                    args += ["-m", t["markers"]]
                # 追加の env が必要なら session.run 前に os.environ[...] = ...
                session.run("pytest", *args, external=True)

@nox.session(python="3.12")
def rust(session: nox.Session) -> None:
    """
    ルート workspace の Rust テストを実行
    """
    # Rust はホストに入っている前提（WSLなら apt / rustup 等）
    session.run("cargo", "test", "--workspace", external=True)

@nox.session
def all(session: nox.Session) -> None:
    """
    Python (pyext) → Rust（workspace）をまとめて
    """
    for s in ("py", "rust"):
        session.notify(s)
