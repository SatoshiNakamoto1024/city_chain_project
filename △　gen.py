# tools/gen.py
# =====================================================================================
# services.yaml から以下を生成:
#   1) docker-bake.generated.hcl        … 並列ビルド定義
#   2) docker-compose.test.generated.yml… infra→services→tests を一括起動
#   3) docker-compose.prod.generated.yml… 本番起動
#
# 使い方:
#   python tools/gen.py --services services.yaml --out .
#
# 依存: pip install pyyaml
# 前提: リポジトリ直下に共通 Dockerfile（汎用 ARG 版）があること
#       - ARG CRATE_PATH / CRATE_KIND / FEATURES / BIN_NAME / PROFILE を受ける
# =====================================================================================

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
import textwrap
from typing import Any, Dict, List, Tuple

import yaml

# 先頭に何も足さない（BOM/---/コメントを避ける）
GEN_HEADER = ""

# -------------------------------------------------------------------------------------
# Utils
# -------------------------------------------------------------------------------------


def eprint(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # UTF-8 / 改行 \n / 先頭に余計なものは出さない
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(GEN_HEADER + content)
    eprint(f"[gen] wrote {path}")


def crate_root_from_crate_path(crate_path: str) -> str:
    """
    Dockerfile の ARG CRATE_PATH は「ドメイン・ルート（*_rust/_python の親）」を期待。
    例:
      DAGs/.../rvh_trace/rvh_trace_rust               -> DAGs/.../rvh_trace
      DAGs/.../poh_holdmetrics/poh_holdmetrics_rust   -> DAGs/.../poh_holdmetrics
    """
    p = Path(crate_path)
    return str(p.parent) if p.name.endswith("_rust") else str(p)


def join_features(features: List[str] | None) -> str:
    if not features:
        return ""
    return ",".join(features)

# -------------------------------------------------------------------------------------
# Bake (buildx) generator
# -------------------------------------------------------------------------------------


def generate_bake_hcl(cfg: Dict[str, Any]) -> str:
    defaults = cfg.get("defaults", {})
    dockerfile = defaults.get("dockerfile", "./Dockerfile")

    target_names: List[str] = []
    target_blocks: List[str] = []

    # pyext → build stage（wheel 作成）
    for px in (cfg.get("pyext", []) or []):
        name = px["name"]
        crate_root = crate_root_from_crate_path(px["crate_path"])
        kind = px.get("kind", "mixed")
        features = join_features(px.get("features"))
        tname = f"{name}-pyext"
        target_names.append(tname)

        target_blocks.append(textwrap.dedent(f"""
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
            "org.opencontainers.image.title"       = "{name}-pyext"
            "org.opencontainers.image.source"      = "services.yaml"
            "org.opencontainers.image.description" = "Build stage for {name} (pyext wheel)"
          }}
        }}
        """).strip())

    # services → runtime stage（実行イメージ）
    for svc in (cfg.get("services", []) or []):
        name = svc["name"]
        crate_root = crate_root_from_crate_path(svc["crate_path"])
        kind = svc.get("kind", "rust")
        features = join_features(svc.get("features"))
        bin_name = svc.get("bin_name", "")
        tname = f"{name}-svc"
        target_names.append(tname)

        target_blocks.append(textwrap.dedent(f"""
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
            "org.opencontainers.image.title"       = "{name}-svc"
            "org.opencontainers.image.source"      = "services.yaml"
            "org.opencontainers.image.description" = "Runtime image for service {name}"
          }}
        }}
        """).strip())

    # 先に group ブロックだけを閉じて出力、その後で target ブロック群を並べる
    group_block = "group \"default\" {\n  targets = [\n"
    for t in target_names:
        group_block += f'    "{t}",\n'
    group_block += "  ]\n}\n"

    return group_block + "\n\n".join(target_blocks) + "\n"

# -------------------------------------------------------------------------------------
# Compose generators（services を必ず先頭に）
# -------------------------------------------------------------------------------------


def _healthcheck_tcp_block(port_env: str | None, port_literal: int | None,
                           interval: str, timeout: str, retries: int) -> List[str]:
    if port_env:
        py = f"import os,socket; p=int(os.environ.get('{port_env}','0') or 0); s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',p)); s.close()"
    elif port_literal is not None:
        py = f"import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',{port_literal})); s.close()"
    else:
        py = "import sys; sys.exit(1)"
    lines: List[str] = []
    lines.append("    healthcheck:")
    lines.append(f'      test: ["CMD","python","-c","{py}"]')
    lines.append(f"      interval: {interval}")
    lines.append(f"      timeout: {timeout}")
    lines.append(f"      retries: {retries}")
    return lines


def _compose_infra_services(cfg: Dict[str, Any]) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """infra セクションを services: の子要素として出力する。"""
    network = cfg.get("defaults", {}).get("network", "city_chain_net")
    services_lines: List[str] = []
    volume_map: Dict[str, Dict[str, str]] = {}

    for infra in cfg.get("infra", []) or []:
        name = infra["name"]
        services_lines.append(f"  {name}:")
        services_lines.append(f'    image: "{infra["image"]}"')
        if infra.get("ports"):
            services_lines.append("    ports:")
            for p in infra["ports"]:
                services_lines.append(f'      - "{p}"')
        if infra.get("volumes"):
            services_lines.append("    volumes:")
            for v in infra["volumes"]:
                volname = v["name"]
                services_lines.append(f"      - {volname}:{v['mount']}")
                volume_map.setdefault(volname, {"driver": v.get("driver", "local")})
        if infra.get("healthcheck"):
            hc = infra["healthcheck"]
            services_lines.append("    healthcheck:")
            if hc.get("type") == "mongosh":
                cmd = hc.get("command", "db.adminCommand({ping:1})").replace('"', '\\"')
                services_lines.append(f'      test: ["CMD-SHELL","mongosh --quiet --eval \\"{cmd}\\""]')
            else:
                services_lines.append('      test: ["CMD-SHELL","echo ok"]')
            services_lines.append(f"      interval: {hc.get('interval', '5s')}")
            services_lines.append(f"      timeout: {hc.get('timeout', '2s')}")
            services_lines.append(f"      retries: {int(hc.get('retries', 20))}")
        services_lines.append("    networks:")
        services_lines.append(f"      - {network}")
        services_lines.append("")  # 空行で区切る

    return services_lines, volume_map


def _compose_app_and_tests_services(cfg: Dict[str, Any], include_tests: bool) -> List[str]:
    """services と（必要なら）pyext/tests を services: の子要素として出力する。"""
    defaults = cfg.get("defaults", {})
    dockerfile = defaults.get("dockerfile", "./Dockerfile")
    network = defaults.get("network", "city_chain_net")

    out: List[str] = []

    # 利用可否の検出（テスト用の自動 depends_on / env 注入に使う）
    service_names = {s["name"] for s in (cfg.get("services", []) or [])}
    infra_names = {i["name"] for i in (cfg.get("infra", []) or [])}
    has_mongo = "mongo" in infra_names
    has_grpc = "poh_holdmetrics-grpc" in service_names
    has_http = "poh_holdmetrics-http" in service_names

    # 常駐 services
    for svc in cfg.get("services", []) or []:
        name = svc["name"]
        crate_root = crate_root_from_crate_path(svc["crate_path"])
        kind = svc.get("kind", "rust")
        features = join_features(svc.get("features"))
        bin_name = svc.get("bin_name", "")
        out.append(f"  {name}:")
        out.append("    build:")
        out.append("      context: .")
        out.append(f"      dockerfile: {dockerfile}")
        out.append("      target: runtime")
        out.append("      args:")
        out.append(f"        CRATE_PATH: {crate_root}")
        out.append(f"        CRATE_KIND: {kind}")
        out.append(f'        FEATURES: "{features}"')
        if bin_name:
            out.append(f"        BIN_NAME: {bin_name}")
        out.append("        PROFILE: release")
        out.append(f'    image: "${{REGISTRY:-local}}/{name}:latest"')
        if svc.get("env"):
            out.append("    environment:")
            for k, v in svc["env"].items():
                out.append(f'      {k}: "{v}"')
        if svc.get("ports"):
            out.append("    ports:")
            for p in svc["ports"]:
                out.append(f'      - "{p}"')
        # services.yaml の command をそのまま反映
        if svc.get("command"):
            cmd = svc["command"]  # list でも str でもOK
            out.append(f"    command: {cmd}")
        # depends_on（明示分）
        if svc.get("depends_on"):
            out.append("    depends_on:")
            for dep in svc["depends_on"]:
                out.append(f"      {dep}:")
                out.append("        condition: service_healthy")
        # healthcheck（明示が無ければ -grpc/-http の名前規約でデフォルト付与）
        if svc.get("healthcheck"):
            hc = svc["healthcheck"]
            out.extend(_healthcheck_tcp_block(
                hc.get("port_env"), hc.get("port"),
                hc.get("interval", "5s"), hc.get("timeout", "2s"),
                int(hc.get("retries", 10))
            ))
        else:
            # 名前規約で自動ヘルスチェック
            if name.endswith("-grpc"):
                out.extend(_healthcheck_tcp_block(None, 60051, "2s", "1s", 60))
            elif name.endswith("-http"):
                out.extend(_healthcheck_tcp_block(None, 8000, "2s", "1s", 60))
        out.append("    networks:")
        out.append(f"      - {network}")
        out.append("")

    if not include_tests:
        return out

    # pyext テスト（oneshot）
    for px in cfg.get("pyext", []) or []:
        name = px["name"]
        crate_root = crate_root_from_crate_path(px["crate_path"])
        kind = px.get("kind", "mixed")
        features = join_features(px.get("features") or ["python"])
        wrapper = px.get("python_wrapper")

        for i, t in enumerate(px.get("tests", []) or [], start=1):
            tname = f"test-{name}-{i}"
            out.append(f"  {tname}:")
            out.append("    build:")
            out.append("      context: .")
            out.append(f"      dockerfile: {dockerfile}")
            out.append("      target: build")
            out.append("      args:")
            out.append(f"        CRATE_PATH: {crate_root}")
            out.append(f"        CRATE_KIND: {kind}")
            out.append(f'        FEATURES: "{features}"')
            out.append("        PROFILE: release")
            out.append(f'    image: "${{REGISTRY:-local}}/{tname}:latest"')
            out.append("    working_dir: /workspace")
            # --- collect env for tests and emit once ---
            env = {}
            # 既存のテスト定義から env を拾う（もしあれば）
            if t.get("environment"):
                env.update(t["environment"])
            if t.get("env"):
                env.update(t["env"])
            # Mongo 接続先（未指定ならだけ入れる）
            env.setdefault("MONGODB_URL", "mongodb://mongo:27017")
            env.setdefault("MONGODB_URI", "mongodb://mongo:27017")
            env.setdefault("MONGODB_DB", "pytest_tmp")
            # 兄弟サービスへの自動注入（未設定のときだけ）
            if has_grpc:
                env.setdefault("POH_GRPC_ADDR", "poh_holdmetrics-grpc:60051")
            if has_http:
                env.setdefault("POH_HTTP_ADDR", "http://poh_holdmetrics-http:8000")
            if has_mongo:
                env.setdefault("MONGO_URL", "mongodb://mongo:27017")
            if env:
                out.append("    environment:")
                for k, v in env.items():
                    out.append(f'      {k}: "{v}"')
            # 明示 wait_for があればそれを優先
            explicit_wait = t.get("wait_for")

            # 自動 depends_on: mongo は service_started、-grpc/-http は healthy
            out.append("    depends_on:")
            if explicit_wait:
                out.append(f"      {explicit_wait['service']}:")
                out.append("        condition: service_healthy")
            else:
                if has_mongo:
                    out.append("      mongo:")
                    out.append("        condition: service_healthy")
                if has_grpc:
                    out.append("      poh_holdmetrics-grpc:")
                    out.append("        condition: service_healthy")
                if has_http:
                    out.append("      poh_holdmetrics-http:")
                    out.append("        condition: service_healthy")

            if t.get("kind") == "pytest":
                path = t["path"]
                markers = t.get("markers")
                # 先に Rust 拡張 wheel をインストール → その後に Python ラッパを -e で入れる
                cmd = (
                    "set -eux; "
                    # maturin build 済みの成果物（/workspace/wheels）を入れる
                    "if ls /workspace/wheels/*.whl >/dev/null 2>&1; then "
                    "  python -m pip install --no-cache-dir /workspace/wheels/*.whl; "
                    "else "
                    "  echo '!! no wheels found under /workspace/wheels' >&2; "
                    "fi; "
                    # ラッパ（テスト extras 付き）を editable で
                    f"python -m pip install --no-cache-dir -e {wrapper}[test]; "
                    # pytest 実行
                    f"pytest -q {path}"
                )
                if markers:
                    cmd += f" -m \"{markers}\""
                out.append(f"    command: bash -lc {shlex.quote(cmd)}")

            out.append("    networks:")
            out.append(f"      - {network}")
            out.append("")

    # services のテスト（oneshot）
    for svc in cfg.get("services", []) or []:
        name = svc["name"]
        crate_root = crate_root_from_crate_path(svc["crate_path"])
        kind = svc.get("kind", "rust")
        features = join_features(svc.get("features"))

        for i, t in enumerate(svc.get("tests", []) or [], start=1):
            tname = f"test-{name}-{i}"
            out.append(f"  {tname}:")
            out.append("    build:")
            out.append("      context: .")
            out.append(f"      dockerfile: {dockerfile}")
            out.append("      target: build")
            out.append("      args:")
            out.append(f"        CRATE_PATH: {crate_root}")
            out.append(f"        CRATE_KIND: {kind}")
            out.append(f'        FEATURES: "{features}"')
            out.append("        PROFILE: release")
            out.append(f'    image: "${{REGISTRY:-local}}/{tname}:latest"')
            out.append("    working_dir: /workspace")
            # --- collect env for tests and emit once ---
            env = {}
            # 既存のテスト定義から env を拾う（もしあれば）
            if t.get("environment"):
                env.update(t["environment"])
            if t.get("env"):
                env.update(t["env"])
            # Mongo 接続先（未指定ならだけ入れる）
            env.setdefault("MONGODB_URL", "mongodb://mongo:27017")
            env.setdefault("MONGODB_URI", "mongodb://mongo:27017")
            env.setdefault("MONGODB_DB", "pytest_tmp")
            if has_grpc:
                env.setdefault("POH_GRPC_ADDR", "poh_holdmetrics-grpc:60051")
            if has_http:
                env.setdefault("POH_HTTP_ADDR", "http://poh_holdmetrics-http:8000")
            if has_mongo:
                env.setdefault("MONGO_URL", "mongodb://mongo:27017")
            if env:
                out.append("    environment:")
                for k, v in env.items():
                    out.append(f'      {k}: "{v}"')
            # 明示 wait_for があればそれを優先
            explicit_wait = t.get("wait_for")
            # 自動 depends_on
            out.append("    depends_on:")
            if has_mongo:
                out.append("      mongo:")
                out.append("        condition: service_healthy")
            if has_grpc:
                out.append("      poh_holdmetrics-grpc:")
                out.append("        condition: service_healthy")
            if has_http:
                out.append("      poh_holdmetrics-http:")
                out.append("        condition: service_healthy")

            if t.get("kind") == "pytest":
                path = t["path"]
                markers = t.get("markers")
                wrapper_guess = svc["crate_path"].replace("_rust", "_python")
                cmd = (
                    "set -eux; "
                    "if ls /workspace/wheels/*.whl >/dev/null 2>&1; then "
                    "  python -m pip install --no-cache-dir /workspace/wheels/*.whl; "
                    "else "
                    "  echo '!! no wheels found under /workspace/wheels' >&2; "
                    "fi; "
                    f"python -m pip install --no-cache-dir -e {wrapper_guess}[test] || true; "
                    f"pytest -q {path}"
                )
                if markers:
                    cmd += f" -m \"{markers}\""
                out.append(f"    command: bash -lc {shlex.quote(cmd)}")

            out.append("    networks:")
            out.append(f"      - {network}")
            out.append("")

    return out


def _network_block(cfg: Dict[str, Any]) -> str:
    network = cfg.get("defaults", {}).get("network", "city_chain_net")
    return f"networks:\n  {network}: {{}}\n"


def _volumes_block(volume_map: Dict[str, Dict[str, str]]) -> str:
    if not volume_map:
        return ""
    lines = ["volumes:"]
    for n, meta in volume_map.items():
        lines.append(f"  {n}:")
        if meta.get("driver"):
            lines.append(f"    driver: {meta['driver']}")
    lines.append("")  # 末尾改行
    return "\n".join(lines)


def generate_compose_test(cfg: Dict[str, Any]) -> str:
    infra_services, volume_map = _compose_infra_services(cfg)
    app_and_tests = _compose_app_and_tests_services(cfg, include_tests=True)

    services_block = "services:\n" + "\n".join(infra_services + app_and_tests) + "\n"
    networks_block = _network_block(cfg)
    volumes_block = _volumes_block(volume_map)
    return services_block + networks_block + volumes_block


def generate_compose_prod(cfg: Dict[str, Any]) -> str:
    infra_services, volume_map = _compose_infra_services(cfg)
    app_only = _compose_app_and_tests_services(cfg, include_tests=False)

    services_block = "services:\n" + "\n".join(infra_services + app_only) + "\n"
    networks_block = _network_block(cfg)
    volumes_block = _volumes_block(volume_map)
    return services_block + networks_block + volumes_block

# -------------------------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate bake/compose files from services.yaml")
    ap.add_argument("--services", type=str, default="services.yaml")
    ap.add_argument("--out", type=str, default=".")
    args = ap.parse_args()

    services_path = Path(args.services).resolve()
    out_dir = Path(args.out).resolve()

    if not services_path.exists():
        eprint(f"[gen] services.yaml not found: {services_path}")
        sys.exit(1)

    cfg = load_yaml(services_path)
    if not isinstance(cfg, dict) or cfg.get("version") != 1:
        eprint("[gen] invalid services.yaml (version: 1 required)")
        sys.exit(1)

    bake = generate_bake_hcl(cfg)
    compose_test = generate_compose_test(cfg)
    compose_prod = generate_compose_prod(cfg)

    write_file(out_dir / "docker-bake.generated.hcl", bake)
    write_file(out_dir / "docker-compose.test.generated.yml", compose_test)
    write_file(out_dir / "docker-compose.prod.generated.yml", compose_prod)
    eprint("[gen] done.")


if __name__ == "__main__":
    main()
