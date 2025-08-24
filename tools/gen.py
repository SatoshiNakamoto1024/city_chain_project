# tools/gen.py
# =====================================================================================
# Generate:
#   1) services.yaml（無ければ初期生成／既存は“許可ドメインだけ”不足分を追記）
#   2) docker-bake.generated.hcl
#   3) docker-compose.test.generated.yml
#   4) docker-compose.prod.generated.yml
#   5) Dockerfile（無ければテンプレ生成。既存は尊重）
#   6) noxfile.py（無ければ生成。--update-nox で上書き）
#
# 設計方針（重要）:
#   - 発見（discovery）はするが、反映は“許可されたドメインのみ”
#   - 既定の許可: {"poh_holdmetrics", "rvh_trace"} だけ
#   - 追加許可: ドメイン直下の .gen.include（空でOK） または .gen.yml(include: true)
#   - 追加許可: CLI --include <name> 複数可
#   - 全許可:   CLI --allow-all を明示した時のみ
#
# 依存: pip install pyyaml
# 実行はリポジトリのルートで。
# =====================================================================================

from __future__ import annotations

import argparse
import os
import shlex
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


# -------------------------------------------------------------------------------------
# 基本ユーティリティ
# -------------------------------------------------------------------------------------

def eprint(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump_yaml(obj: Dict[str, Any]) -> str:
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, default_flow_style=False)


def write_text_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = None
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            old = f.read()
    if old == content:
        eprint(f"[gen] unchanged: {path}")
        return
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    eprint(f"[gen] wrote {path}")


def ensure_relative(path_str: str, repo_root: Path) -> str:
    p = Path(path_str)
    try:
        return str(p.relative_to(repo_root))
    except Exception:
        return path_str


def crate_root_from_crate_path(crate_path: str) -> str:
    p = Path(crate_path)
    return str(p.parent) if p.name.endswith("_rust") else str(p)


def join_features(features: List[str] | None) -> str:
    return ",".join(features or [])


# -------------------------------------------------------------------------------------
# 許可ポリシー
# -------------------------------------------------------------------------------------

DEFAULT_ALLOWED = {"poh_holdmetrics", "rvh_trace"}

def is_marker_allow(domain_dir: Path) -> bool:
    m1 = domain_dir / ".gen.include"
    m2 = domain_dir / ".gen.yml"
    if m1.exists():
        return True
    if m2.exists():
        try:
            data = yaml.safe_load(m2.read_text(encoding="utf-8")) or {}
            return bool(data.get("include"))
        except Exception:
            return False
    return False


def should_include(domain_dir: Path, cli_includes: set[str], allow_all: bool) -> bool:
    name = domain_dir.name
    if allow_all:
        return True
    if name in cli_includes:
        return True
    if name in DEFAULT_ALLOWED:
        return True
    return is_marker_allow(domain_dir)


# -------------------------------------------------------------------------------------
# ドメイン発見（algorithm/<domain> の“1階層”のみ）
# -------------------------------------------------------------------------------------

def find_domains(repo_root: Path, verbose: bool) -> List[Path]:
    alg_root = repo_root / "DAGs" / "libs" / "algorithm"
    if not alg_root.exists():
        if verbose:
            eprint(f"[gen] algorithm root not found: {alg_root}")
        return []
    out: List[Path] = []
    for d in sorted(alg_root.iterdir()):
        if not d.is_dir():
            continue
        rust = d / f"{d.name}_rust"
        py   = d / f"{d.name}_python"
        if rust.exists() or py.exists():
            out.append(d)
    if verbose:
        eprint("[gen] discovered candidates:")
        for d in out:
            eprint(f"  - {d.name}  (rust={ (d / (d.name + '_rust')).exists() }, python={ (d / (d.name + '_python')).exists() })")
    return out


# -------------------------------------------------------------------------------------
# pyext / services ブロック生成
# -------------------------------------------------------------------------------------

def tests_path_for_wrapper(domain_dir: Path) -> str:
    name = domain_dir.name
    wrapper = domain_dir / f"{name}_python"
    pkg_dir = wrapper / name
    tests_dir = pkg_dir / "tests"
    if tests_dir.exists():
        return str(tests_dir)
    # wrapper 配下の最初の tests ディレクトリも許容
    cand = list(wrapper.glob("**/tests"))
    return str(cand[0]) if cand else str(wrapper)


def pyext_block_for_domain(domain_dir: Path) -> Dict[str, Any]:
    name = domain_dir.name
    rust = domain_dir / f"{name}_rust"
    wrapper = domain_dir / f"{name}_python"

    block: Dict[str, Any] = {
        "name": name,
        "crate_path": str(domain_dir),
        "kind": "mixed" if rust.exists() else "python",
        "features": ["python"] if wrapper.exists() else [],
        "tests": [],
    }
    if wrapper.exists():
        block["python_wrapper"] = str(wrapper)
        block["tests"].append({"kind": "pytest", "path": tests_path_for_wrapper(domain_dir), "env": {}})

    # poh_holdmetrics のテスト安定化デフォルト
    if name == "poh_holdmetrics" and block["tests"]:
        block["tests"][0]["env"].update({
            "MONGODB_DB": "pytest_tmp",
            "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION": "python",
            "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION": "3",
            "POH_DISABLE_RUST": "1",
            "PYTEST_ADDOPTS": "-o cache_dir=/tmp/pytest_cache",
        })
    return block


def services_blocks_for_holdmetrics(domain_dir: Path) -> List[Dict[str, Any]]:
    d = domain_dir
    return [
        {
            "name": "poh_holdmetrics-grpc",
            "crate_path": str(d / "poh_holdmetrics_rust"),
            "kind": "rust",
            "bin_name": "main_holdmetrics",
            "env": {
                "SERVICE_MODE": "grpc",
                "GRPC_ADDRESS": "0.0.0.0:60051",
                "MONGODB_URL": "${MONGODB_URL}",
                "MONGODB_DB": "holdmetrics_prod",
            },
            "ports": ["60051:60051", "9100:9100"],
            "command": ["/app/bin/main_holdmetrics", "--grpc-addr", "0.0.0.0:60051"],
            "healthcheck": {"port": 60051, "interval": "5s", "timeout": "2s", "retries": 20},
        },
        {
            "name": "poh_holdmetrics-http",
            "crate_path": str(d / "poh_holdmetrics_rust"),
            "kind": "mixed",
            "features": ["python"],
            "env": {
                "SERVICE_MODE": "http",
                "HTTP_PORT": "8000",
                "MONGODB_URL": "${MONGODB_URL}",
                "MONGODB_DB": "holdmetrics_prod",
            },
            "ports": ["8000:8000"],
            "command": ["python","-m","uvicorn","poh_holdmetrics.api.http_server:app","--host","0.0.0.0","--port","8000"],
            "healthcheck": {"port": 8000, "interval": "5s", "timeout": "2s", "retries": 20},
        },
    ]


# -------------------------------------------------------------------------------------
# services.yaml の初期化 / 追記
# -------------------------------------------------------------------------------------

def initial_services_yaml(allowed_domains: List[Path]) -> Dict[str, Any]:
    cfg: Dict[str, Any] = {
        "version": 1,
        "defaults": {"network": "city_chain_net", "dockerfile": "./Dockerfile"},
        "pyext": [],
        "services": [],
    }
    names = {d.name for d in allowed_domains}
    for d in allowed_domains:
        cfg["pyext"].append(pyext_block_for_domain(d))
    if "poh_holdmetrics" in names:
        cfg["services"].extend(services_blocks_for_holdmetrics(next(d for d in allowed_domains if d.name == "poh_holdmetrics")))
    return cfg


def merge_services_yaml(existing: Dict[str, Any], allowed_domains: List[Path], repo_root: Path) -> Dict[str, Any]:
    cfg = {**existing}
    cfg.setdefault("version", 1)
    cfg.setdefault("defaults", {"network": "city_chain_net", "dockerfile": "./Dockerfile"})
    cfg.setdefault("pyext", [])
    cfg.setdefault("services", [])

    # 既存 name セット
    py_names = {it.get("name") for it in cfg["pyext"] if isinstance(it, dict)}
    svc_names = {it.get("name") for it in cfg["services"] if isinstance(it, dict)}

    # 追記（許可ドメインのみ）
    for d in allowed_domains:
        if d.name not in py_names:
            cfg["pyext"].append(pyext_block_for_domain(d))
            eprint(f"[gen] pyext added: {d.name}")

    # holdmetrics サービス（なければ追記）
    if any(d.name == "poh_holdmetrics" for d in allowed_domains):
        for block in services_blocks_for_holdmetrics(next(d for d in allowed_domains if d.name == "poh_holdmetrics")):
            if block["name"] not in svc_names:
                cfg["services"].append(block)
                eprint(f"[gen] service added: {block['name']}")

    # 絶対パス→相対パスに補正
    for sec in ("pyext", "services"):
        for it in cfg.get(sec, []) or []:
            if "crate_path" in it:
                it["crate_path"] = ensure_relative(it["crate_path"], repo_root)
            if "python_wrapper" in it and it["python_wrapper"]:
                it["python_wrapper"] = ensure_relative(it["python_wrapper"], repo_root)
            if "tests" in it and it["tests"]:
                for t in it["tests"]:
                    if "path" in t:
                        t["path"] = ensure_relative(t["path"], repo_root)
    return cfg


def ensure_services_yaml(path: Path, repo_root: Path, allowed_domains: List[Path]) -> Dict[str, Any]:
    if not path.exists():
        cfg = initial_services_yaml(allowed_domains)
        write_text_if_changed(path, dump_yaml(cfg))
        return cfg

    existing = load_yaml(path)
    if not isinstance(existing, dict) or existing.get("version") != 1:
        raise SystemExit("[gen] invalid services.yaml (version: 1 required)")
    merged = merge_services_yaml(existing, allowed_domains, repo_root)
    write_text_if_changed(path, dump_yaml(merged))
    return merged


# -------------------------------------------------------------------------------------
# Dockerfile（テンプレ）
# -------------------------------------------------------------------------------------

DOCKERFILE_TEMPLATE = """# syntax=docker/dockerfile:1.7-labs

FROM ubuntu:24.04 AS build
ARG DEBIAN_FRONTEND=noninteractive
ARG CRATE_PATH
ARG CRATE_KIND=auto
ARG FEATURES=""
ARG PROFILE=release
ARG BIN_NAME=""

RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt,sharing=locked \\
    set -eux; \\
    apt-get update; \\
    apt-get install -y --no-install-recommends \\
        curl git build-essential pkg-config \\
        libssl-dev llvm clang \\
        python3.12 python3.12-dev python3.12-venv python3-pip \\
        protobuf-compiler libprotobuf-dev; \\
    ln -sf /usr/bin/python3.12 /usr/bin/python; \\
    rm -rf /var/lib/apt/lists/*

ENV RUSTUP_HOME=/opt/rust \\
    CARGO_HOME=/opt/rust \\
    PATH=/opt/rust/bin:$PATH
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --default-toolchain 1.88.0

ENV PIP_BREAK_SYSTEM_PACKAGES=1
RUN --mount=type=cache,id=pip-cache-builder,target=/root/.cache/pip \\
    python -m pip install --no-cache-dir maturin==1.5.1

WORKDIR /workspace
COPY Cargo.toml Cargo.toml
COPY network/DB/mongodb/ network/DB/mongodb/
COPY DAGs/libs/algorithm/ DAGs/libs/algorithm/

RUN mkdir -p /workspace/wheels /workspace/python_wrapper /workspace/bin

RUN --mount=type=cache,id=cargo-registry,target=/opt/rust/registry \\
    --mount=type=cache,id=cargo-git,target=/opt/rust/git \\
    --mount=type=cache,id=cargo-target,target=/workspace/target \\
    set -eux; \\
    RUST_TOML="$(ls ${CRATE_PATH}/*_rust/Cargo.toml 2>/dev/null | head -n1 || true)"; \\
    WRAP_DIR="$(ls -d ${CRATE_PATH}/*_python 2>/dev/null | head -n1 || true)"; \\
    if [ -n "${WRAP_DIR}" ]; then cp -a "${WRAP_DIR}/." /workspace/python_wrapper/; fi; \\
    if [ "${CRATE_KIND}" = "mixed" ] || { [ "${CRATE_KIND}" = "auto" ] && [ -n "${RUST_TOML}" ] && [ -d /workspace/python_wrapper ]; }; then \\
        MATURIN_FLAGS="--profile ${PROFILE}"; \\
        if [ -n "${FEATURES}" ]; then MATURIN_FLAGS="$MATURIN_FLAGS --features ${FEATURES}"; fi; \\
        maturin build -m "${RUST_TOML}" ${MATURIN_FLAGS} --out /workspace/wheels; \\
    elif [ "${CRATE_KIND}" = "rust" ]; then \\
        if [ -z "${RUST_TOML}" ]; then echo "!! *_rust/Cargo.toml not found under ${CRATE_PATH}"; exit 1; fi; \\
        if [ -z "${BIN_NAME}" ]; then echo "!! kind=rust には BIN_NAME が必須です"; exit 1; fi; \\
        cargo build --release --manifest-path "${RUST_TOML}"; \\
        cp -v "$(find /workspace/target/release -maxdepth 1 -type f -name ${BIN_NAME})" "/workspace/bin/${BIN_NAME}"; \\
    fi

FROM python:3.12-slim AS runtime
ARG CRATE_KIND=auto
ARG FEATURES=""
ARG PROFILE=release
ARG BIN_NAME=""
ENV CRATE_KIND=${CRATE_KIND} FEATURES=${FEATURES} PROFILE=${PROFILE} BIN_NAME=${BIN_NAME}
WORKDIR /app

RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt,sharing=locked \\
    set -eux; apt-get update; apt-get install -y --no-install-recommends ca-certificates libssl3; \\
    rm -rf /var/lib/apt/lists/*

COPY --from=build /workspace/wheels /wheels
RUN --mount=type=cache,id=pip-cache-runtime,target=/root/.cache/pip \\
    set -eux; \\
    if [ "${CRATE_KIND}" = "python" ] || [ "${CRATE_KIND}" = "mixed" ] || [ "${CRATE_KIND}" = "auto" ]; then \\
        if ls /wheels/*.whl >/dev/null 2>&1; then python -m pip install --no-cache-dir /wheels/*.whl; fi; \\
    fi

COPY --from=build /workspace/python_wrapper /tmp/python_wrapper
RUN --mount=type=cache,id=pip-cache-runtime,target=/root/.cache/pip \\
    set -eux; \\
    if [ "${CRATE_KIND}" != "rust" ] && [ -d /tmp/python_wrapper ] && [ "$(ls -A /tmp/python_wrapper)" ]; then \\
        python -m pip install --no-cache-dir -e /tmp/python_wrapper; \\
    fi

COPY --from=build /workspace/bin /app/bin

CMD ["sh","-lc","echo 'override CMD via compose' && tail -f /dev/null"]
"""

def ensure_dockerfile(dockerfile_path: Path) -> None:
    if dockerfile_path.exists():
        eprint(f"[gen] Dockerfile exists, skip: {dockerfile_path}")
        return
    dockerfile_path.parent.mkdir(parents=True, exist_ok=True)
    dockerfile_path.write_text(DOCKERFILE_TEMPLATE, encoding="utf-8", newline="\n")
    eprint(f"[gen] wrote {dockerfile_path}")


# -------------------------------------------------------------------------------------
# Buildx bake
# -------------------------------------------------------------------------------------

def generate_bake_hcl(cfg: Dict[str, Any]) -> str:
    defaults = cfg.get("defaults", {}) or {}
    dockerfile = defaults.get("dockerfile", "./Dockerfile")

    targets: List[str] = []
    blocks: List[str] = []

    # pyext
    for px in (cfg.get("pyext") or []):
        name = px["name"]
        crate_root = crate_root_from_crate_path(px["crate_path"])
        kind = px.get("kind", "mixed")
        features = join_features(px.get("features"))
        tname = f"{name}-pyext"
        targets.append(tname)
        blocks.append(textwrap.dedent(f"""
        target "{tname}" {{
          context    = "."
          dockerfile = "{dockerfile}"
          target     = "build"
          args = {{
            CRATE_PATH  = "{crate_root}"
            CRATE_KIND  = "{kind}"
            FEATURES    = "{features}"
            PROFILE     = "release"
          }}
          labels = {{
            "org.opencontainers.image.title"       = "{tname}"
            "org.opencontainers.image.source"      = "services.yaml"
            "org.opencontainers.image.description" = "Build stage for {name} (pyext)"
          }}
        }}
        """).strip())

    # services
    for s in (cfg.get("services") or []):
        name = s["name"]
        crate_root = crate_root_from_crate_path(s["crate_path"])
        kind = s.get("kind", "rust")
        features = join_features(s.get("features"))
        bin_name = s.get("bin_name", "")
        tname = f"{name}-svc"
        targets.append(tname)
        blocks.append(textwrap.dedent(f"""
        target "{tname}" {{
          context    = "."
          dockerfile = "{dockerfile}"
          target     = "runtime"
          args = {{
            CRATE_PATH  = "{crate_root}"
            CRATE_KIND  = "{kind}"
            FEATURES    = "{features}"
            BIN_NAME    = "{bin_name}"
            PROFILE     = "release"
          }}
          labels = {{
            "org.opencontainers.image.title"       = "{tname}"
            "org.opencontainers.image.source"      = "services.yaml"
            "org.opencontainers.image.description" = "Runtime image for {name}"
          }}
        }}
        """).strip())

    group = "group \"default\" {\n  targets = [\n" + "".join(f'    "{t}",\n' for t in targets) + "  ]\n}\n"
    return group + ("\n\n".join(blocks) + "\n" if blocks else "\n")


# -------------------------------------------------------------------------------------
# docker-compose (prod/test)
# -------------------------------------------------------------------------------------

def _healthcheck_tcp_block(port: int, interval="5s", timeout="2s", retries=20) -> List[str]:
    py = f"import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',{port})); s.close()"
    return [
        "    healthcheck:",
        f'      test: ["CMD","python","-c","{py}"]',
        f"      interval: {interval}",
        f"      timeout: {timeout}",
        f"      retries: {int(retries)}",
    ]


def _compose_services(cfg: Dict[str, Any], include_tests: bool) -> List[str]:
    defaults = cfg.get("defaults", {}) or {}
    dockerfile = defaults.get("dockerfile", "./Dockerfile")
    network = defaults.get("network", "city_chain_net")

    out: List[str] = []

    # 常駐 services
    for s in (cfg.get("services") or []):
        name = s["name"]
        crate_root = crate_root_from_crate_path(s["crate_path"])
        kind = s.get("kind", "rust")
        features = join_features(s.get("features"))
        bin_name = s.get("bin_name", "")

        out += [
            f"  {name}:",
            "    build:",
            "      context: .",
            f"      dockerfile: {dockerfile}",
            "      target: runtime",
            "      args:",
            f"        CRATE_PATH: {crate_root}",
            f"        CRATE_KIND: {kind}",
            f'        FEATURES: "{features}"',
        ]
        if bin_name:
            out.append(f"        BIN_NAME: {bin_name}")
        out += [
            "        PROFILE: release",
            f'    image: "${{REGISTRY:-local}}/{name}:latest"',
        ]

        if s.get("env"):
            out.append("    environment:")
            for k, v in s["env"].items():
                out.append(f'      {k}: "{v}"')

        if s.get("ports"):
            out.append("    ports:")
            for p in s["ports"]:
                out.append(f'      - "{p}"')

        if s.get("command"):
            out.append(f"    command: {s['command']}")

        if s.get("healthcheck"):
            hc = s["healthcheck"]
            out += _healthcheck_tcp_block(int(hc.get("port", 0)),
                                          hc.get("interval", "5s"),
                                          hc.get("timeout", "2s"),
                                          int(hc.get("retries", 20)))
        else:
            if name.endswith("-grpc"):
                out += _healthcheck_tcp_block(60051, "2s", "1s", 60)
            if name.endswith("-http"):
                out += _healthcheck_tcp_block(8000, "2s", "1s", 60)

        out += ["    networks:", f"      - {network}", ""]

    if not include_tests:
        return out

    # pyext tests
    svc_names = {s["name"] for s in (cfg.get("services") or [])}
    has_grpc = any(n.endswith("-grpc") for n in svc_names)
    has_http = any(n.endswith("-http") for n in svc_names)

    for px in (cfg.get("pyext") or []):
        name = px["name"]
        crate_root = crate_root_from_crate_path(px["crate_path"])
        kind = px.get("kind", "mixed")
        features = join_features(px.get("features") or (["python"] if kind != "rust" else []))
        wrapper = px.get("python_wrapper")

        for i, t in enumerate(px.get("tests") or [], start=1):
            tname = f"test-{name}-{i}"
            out += [
                f"  {tname}:",
                "    build:",
                "      context: .",
                f"      dockerfile: {dockerfile}",
                "      target: build",
                "      args:",
                f"        CRATE_PATH: {crate_root}",
                f"        CRATE_KIND: {kind}",
                f'        FEATURES: "{features}"',
                "        PROFILE: release",
                f'    image: "${{REGISTRY:-local}}/{tname}:latest"',
                "    working_dir: /workspace",
            ]
            env: Dict[str, str] = {}
            if t.get("environment"):
                env.update(t["environment"])
            if t.get("env"):
                env.update(t["env"])
            if has_grpc:
                env.setdefault("POH_GRPC_ADDR", "poh_holdmetrics-grpc:60051")
            if has_http:
                env.setdefault("POH_HTTP_ADDR", "http://poh_holdmetrics-http:8000")
            if env:
                out.append("    environment:")
                for k, v in env.items():
                    out.append(f'      {k}: "{v}"')

            out += ["    depends_on:"]
            if has_grpc:
                out += ["      poh_holdmetrics-grpc:", "        condition: service_healthy"]
            if has_http:
                out += ["      poh_holdmetrics-http:", "        condition: service_healthy"]

            if t.get("kind") == "pytest":
                path = t["path"]
                prelude = (
                    "set -eux; "
                    "python -m pip uninstall -y poh-holdmetrics-rust || true; "
                    "if ls /workspace/wheels/poh_holdmetrics_rust-*.whl >/dev/null 2>&1; then "
                    "  python -m pip install --no-cache-dir /workspace/wheels/poh_holdmetrics_rust-*.whl; "
                    "fi; "
                )
                if wrapper:
                    prelude += f"python -m pip install --no-cache-dir -e {shlex.quote(wrapper)}[test]; "
                prelude += 'exec "$0" "$@"'
                out.append(f'    entrypoint: ["bash","-lc",{shlex.quote(prelude)}]')
                out.append(f'    command: ["pytest","-q","{path}"]')

            out += ["    networks:", f"      - {network}", ""]

    return out


def generate_compose(cfg: Dict[str, Any], include_tests: bool) -> str:
    lines = ["services:"]
    lines += _compose_services(cfg, include_tests=include_tests)
    networks = cfg.get("defaults", {}).get("network", "city_chain_net")
    lines += ["networks:", f"  {networks}: {{}}", ""]
    return "\n".join(lines)


# -------------------------------------------------------------------------------------
# noxfile.py（テンプレ）
# -------------------------------------------------------------------------------------

NOXFILE_TEMPLATE = """\
# noxfile.py (generated)
import yaml, nox
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).parent
SERVICES_YAML = ROOT / "services.yaml"

def load_cfg() -> Dict[str, Any]:
    with SERVICES_YAML.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def crate_root_from_crate_path(crate_path: str) -> Path:
    p = Path(crate_path)
    return p.parent if p.name.endswith("_rust") else p

def maturin_develop(session: nox.Session, crate_toml: Path, features: List[str] | None) -> None:
    cmd = ["maturin", "develop", "-m", str(crate_toml), "--release", "--quiet"]
    if features: cmd += ["--features", ",".join(features)]
    session.run(*cmd, external=True)

@nox.session(python="3.12")
def py(session: nox.Session) -> None:
    cfg = load_cfg()
    pyexts = cfg.get("pyext", []) or []
    session.install("maturin==1.5.1", "pytest>=8,<9", "pyyaml>=6")
    for px in pyexts:
        kind = px.get("kind", "mixed")
        if kind not in ("mixed","python"):
            continue
        crate_path = px["crate_path"]
        crate_root = crate_root_from_crate_path(crate_path)
        rust_dir = crate_root / f"{Path(crate_root).name}_rust"
        rust_toml = rust_dir / "Cargo.toml"
        features = px.get("features") or ["python"]
        wrapper  = px.get("python_wrapper")
        if rust_toml.exists() and kind == "mixed":
            maturin_develop(session, rust_toml, features=features)
        if wrapper:
            session.install("-e", f"{wrapper}[test]")
        for t in px.get("tests") or []:
            if t.get("kind") == "pytest":
                args = ["-q", t["path"]]
                session.run("pytest", *args, external=True)

@nox.session(python=False)
def rust(session: nox.Session) -> None:
    session.run("cargo", "test", "--workspace", external=True)

@nox.session
def all(session: nox.Session) -> None:
    for s in ("py","rust"):
        session.notify(s)
"""


def maybe_write_noxfile(repo_root: Path, force: bool) -> None:
    target = repo_root / "noxfile.py"
    if target.exists() and not force:
        eprint("[gen] noxfile.py exists, skip (use --update-nox to overwrite)")
        return
    target.write_text(NOXFILE_TEMPLATE, encoding="utf-8", newline="\n")
    eprint(f"[gen] wrote {target}")


# -------------------------------------------------------------------------------------
# メイン
# -------------------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Generate build/compose from services.yaml")
    ap.add_argument("--services", type=str, default="services.yaml")
    ap.add_argument("--out", type=str, default=".")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--include", action="append", default=[], help="extra domain name to include (repeatable)")
    ap.add_argument("--allow-all", action="store_true", help="include all discovered domains (danger)")
    ap.add_argument("--update-nox", action="store_true", help="overwrite existing noxfile.py")
    args = ap.parse_args()

    repo_root = Path(".").resolve()
    services_path = (repo_root / args.services).resolve()
    out_dir = Path(args.out).resolve()

    # 候補の発見
    candidates = find_domains(repo_root, verbose=args.verbose)
    includes_cli = set(args.include or [])
    allowed = [d for d in candidates if should_include(d, includes_cli, args.allow_all)]

    if args.verbose:
        eprint("[gen] allowed domains:")
        for d in allowed:
            eprint(f"  - {d.name}")

    # Dockerfile（無ければ）
    ensure_dockerfile(repo_root / "Dockerfile")

    # services.yaml（初回生成 or 追記）
    cfg = ensure_services_yaml(services_path, repo_root, allowed)

    # 生成ファイル
    write_text_if_changed(out_dir / "docker-bake.generated.hcl", generate_bake_hcl(cfg))
    write_text_if_changed(out_dir / "docker-compose.test.generated.yml", generate_compose(cfg, include_tests=True))
    write_text_if_changed(out_dir / "docker-compose.prod.generated.yml", generate_compose(cfg, include_tests=False))

    # noxfile.py
    maybe_write_noxfile(repo_root, force=args.update_nox)

    eprint("[gen] done.")


if __name__ == "__main__":
    main()
