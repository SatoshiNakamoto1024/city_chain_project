# D:\city_chain_project\network\DAGs\rust\MAINTENANCE_PLAN.md
# 解説:この Markdown で「Rust↔Python のビルド→テスト→リリース」をどのように進めるかを ドキュメント化 しています。
# ここに API互換性の方針 や CIワークフロー などを追記していけば、メンテナンス計画としてチームで共有できます。

# Maintenance Plan for the Rust-Python DAG Project

This document outlines how we maintain, update, and release the Rust library (`federation_dag`) and ensure smooth integration with Python code.

---

## 1. Repository Structure

repo_root/ ├── python/ │ ├── city_level/ │ ├── continent_level/ │ ├── global_level/ │ ├── common/ │ ├── tests/ │ └── ... ├── rust/ │ ├── Cargo.toml │ ├── pyproject.toml │ ├── MAINTENANCE_PLAN.md (this file) │ └── src/ │ ├── lib.rs │ └── ntru_dilithium.rs └── ...


## 2. Workflow: Development & CI

1. **Local Development**
   - Make changes in Rust code under `src/`.
   - Run `maturin develop` (in the `rust/` directory) to build and install the Python extension module in your virtualenv.
   - Then run `pytest` in `python/tests/` to ensure that both Rust unit tests and Python integration tests pass.

2. **Rust Unit Tests**
   - In `rust/` directory:
     ```bash
     cargo test
     ```
   - This verifies purely Rust-side logic, like concurrency, data structures, etc.

3. **Python Tests**
   - In `python/` directory (or `python/tests/`):
     ```bash
     pytest
     ```
   - This checks DAG logic in Python, plus integration with the `federation_dag` library.

4. **CI Pipeline**
   - (Example: GitHub Actions)
   - On pull request:
     1) `cargo test`
     2) `maturin build --release` → produce a wheel
     3) Install the wheel in a Python venv
     4) `pytest` for Python + integration tests
   - If all pass, we merge.

## 3. Versioning

- We use Semantic Versioning for the Rust crate.
  - `0.x.y` for initial development.
  - Once stable, `1.x.y` with backward compatibility guaranteed unless major version increments.
- Python code depends on `federation_dag` by version constraints, e.g. `federation_dag>=0.1.0,<0.2.0`.

## 4. Breaking Changes

- When altering the function signatures or data structures that Python calls, we increment the **major** or **minor** version.
- We update Python code accordingly, ensuring our tests in `test_rust_integration.py` reflect the new calls.

## 5. Release Process

1. Bump version in `Cargo.toml`.
2. Commit & tag (`git tag v0.2.0` etc.).
3. `maturin build --release` → upload wheel to PyPI or internal PyPI-like index if needed.
4. Update the Python code to reference the new version in `requirements.txt` or other config.

## 6. Future Extension

- For real NTRU & Dilithium, replace `ntru_dilithium.rs` stubs with actual crates or FFI calls.
- Possibly add advanced DAG concurrency logic with PBFT or advanced DPoS in Rust.
- Keep Python side as the orchestrator for node management, PoP logic, networking.

---

**END**
