# syntax=docker/dockerfile:1.7-labs

# Dockerfile（汎用・本番想定）
# CRATE_KIND: auto|python|rust|mixed
#   - python: Pure Python パッケージのみ
#   - rust  : Rust バイナリのみ（pyo3 なし）
#   - mixed : pyo3（maturin）で Python 拡張 + 任意で純Pythonラッパ
# FEATURES  : maturin に渡す features（例: python,grpc など）
# PROFILE   : release / dev
# BIN_NAME  : kind=rust の時にできる実行バイナリ名（必須）

########################  builder  ########################
FROM ubuntu:24.04 AS build
ARG DEBIAN_FRONTEND=noninteractive
ARG CRATE_PATH
ARG CRATE_KIND=auto
ARG FEATURES=""
ARG PROFILE=release
ARG BIN_NAME=""

# 1) OSパッケージ
#    - /var/cache/apt だけを cache mount（sharing=locked で並列ビルドでも安全）
#    - /var/lib/apt/lists はキャッシュしない（ロック競合の原因になるため）
RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt,sharing=locked \
    set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        curl git build-essential pkg-config \
        libssl-dev llvm clang \
        python3.12 python3.12-dev python3.12-venv python3-pip \
        protobuf-compiler libprotobuf-dev; \
    ln -sf /usr/bin/python3.12 /usr/bin/python; \
    rm -rf /var/lib/apt/lists/*

# 2) Rust
ENV RUSTUP_HOME=/opt/rust \
    CARGO_HOME=/opt/rust \
    PATH=/opt/rust/bin:$PATH
RUN curl -sSf https://sh.rustup.rs \
    | sh -s -- -y --no-modify-path --default-toolchain 1.88.0

# 3) Pythonツール
ENV PIP_BREAK_SYSTEM_PACKAGES=1
RUN --mount=type=cache,id=pip-cache-builder,target=/root/.cache/pip \
    python -m pip install --no-cache-dir maturin==1.5.1

# 4) ソース配置（.dockerignore で不要物は除外推奨）
WORKDIR /workspace
COPY Cargo.toml Cargo.toml
COPY DAGs/libs/algorithm/ DAGs/libs/algorithm/

# 5) 出力用ディレクトリ
RUN mkdir -p /workspace/wheels /workspace/python_wrapper /workspace/bin

# 6) Rust/Maturin/Python の分岐ビルド
#    - cargo の registry/git/target をキャッシュ
RUN --mount=type=cache,id=cargo-registry,target=/opt/rust/registry \
    --mount=type=cache,id=cargo-git,target=/opt/rust/git \
    --mount=type=cache,id=cargo-target,target=/workspace/target \
    set -eux; \
    RUST_TOML="$(ls ${CRATE_PATH}/*_rust/Cargo.toml 2>/dev/null | head -n1 || true)"; \
    WRAP_DIR="$(ls -d ${CRATE_PATH}/*_python 2>/dev/null | head -n1 || true)"; \
    if [ -n "${WRAP_DIR}" ]; then \
        echo ">> Found python wrapper: ${WRAP_DIR}"; \
        cp -a "${WRAP_DIR}/." /workspace/python_wrapper/; \
    else \
        echo ">> No python wrapper"; \
    fi; \
    if [ "${CRATE_KIND}" = "mixed" ] || { [ "${CRATE_KIND}" = "auto" ] && [ -n "${RUST_TOML}" ] && [ -d /workspace/python_wrapper ]; }; then \
        echo ">> Building as MIXED via maturin"; \
        MATURIN_FLAGS="--profile ${PROFILE}"; \
        if [ -n "${FEATURES}" ]; then MATURIN_FLAGS="$MATURIN_FLAGS --features ${FEATURES}"; fi; \
        maturin build -m "${RUST_TOML}" ${MATURIN_FLAGS} --out /workspace/wheels; \
    elif [ "${CRATE_KIND}" = "rust" ]; then \
        echo ">> Building as RUST (cargo build)"; \
        if [ -z "${RUST_TOML}" ]; then echo "!! *_rust/Cargo.toml not found under ${CRATE_PATH}"; exit 1; fi; \
        if [ -z "${BIN_NAME}" ]; then echo "!! kind=rust には BIN_NAME が必須です"; exit 1; fi; \
        cargo build --release --manifest-path "${RUST_TOML}"; \
        cp -v "$(find /workspace/target/release -maxdepth 1 -type f -name ${BIN_NAME})" "/workspace/bin/${BIN_NAME}"; \
    else \
        echo ">> Building as PYTHON-ONLY (no Rust build)"; \
    fi

########################  runtime  ########################
FROM python:3.12-slim AS runtime
# build 引数は段をまたぐので再宣言
ARG CRATE_KIND=auto
ARG FEATURES=""
ARG PROFILE=release
ARG BIN_NAME=""

# ★ ランタイムで参照できるように ENV に昇格（重要）
ENV CRATE_KIND=${CRATE_KIND} \
    FEATURES=${FEATURES} \
    PROFILE=${PROFILE} \
    BIN_NAME=${BIN_NAME}

WORKDIR /app

# Rust バイナリのランタイム依存（必要最小限）
RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt,sharing=locked \
    set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates libssl3; \
    rm -rf /var/lib/apt/lists/*

# 1) wheels（python/mixed/auto の時だけ）
COPY --from=build /workspace/wheels /wheels
RUN --mount=type=cache,id=pip-cache-runtime,target=/root/.cache/pip \
    set -eux; \
    if [ "${CRATE_KIND}" = "python" ] || [ "${CRATE_KIND}" = "mixed" ] || [ "${CRATE_KIND}" = "auto" ]; then \
        if ls /wheels/*.whl >/dev/null 2>&1; then \
            echo ">> Installing wheels..."; \
            python -m pip install --no-cache-dir /wheels/*.whl; \
        else \
            echo ">> No wheels to install"; \
        fi; \
    else \
        echo ">> CRATE_KIND=${CRATE_KIND}: skip wheel install"; \
    fi

# 2) python_wrapper（rust の時はスキップ）
COPY --from=build /workspace/python_wrapper /tmp/python_wrapper
RUN --mount=type=cache,id=pip-cache-runtime,target=/root/.cache/pip \
    set -eux; \
    if [ "${CRATE_KIND}" = "rust" ]; then \
        echo ">> rust runtime: skip python wrapper install"; \
    else \
        if [ -d /tmp/python_wrapper ] && [ "$(ls -A /tmp/python_wrapper)" ]; then \
            echo ">> Installing editable python wrapper..."; \
            python -m pip install --no-cache-dir -e /tmp/python_wrapper; \
        else \
            echo ">> No python wrapper to install"; \
        fi; \
    fi

# 3) rust-only バイナリ（あれば）
COPY --from=build /workspace/bin /app/bin

# デフォルト CMD（compose 側で上書き前提）
CMD ["/bin/sh", "-lc", "\
  case \"$SERVICE_MODE\" in \
    grpc) exec /app/bin/main_holdmetrics --grpc-addr "${GRPC_ADDRESS:-0.0.0.0:60051}" --metrics-addr "${METRICS_ADDRESS:-0.0.0.0:9100}" ;; \
    http) exec python -m uvicorn poh_holdmetrics.api.http_server:app --host 0.0.0.0 --port \"${HTTP_PORT:-8000}\" ;; \
    *)    echo 'unknown SERVICE_MODE; sleeping' ; tail -f /dev/null ;; \
  esac"]