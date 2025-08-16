# PoP Algorithmにおいて、
以下は 「開発者がローカルでビルドを確認済み」 という前提で、
GitHub Actions による CI／自動配布 を完成させ、
最終的に利用者が pip install できる状態 へ至るまでを
作業順に 1 ステップずつ並べた手順書です。

❶ リポジトリ構成を確定する
repo-root/
├─ .github/
│   └─ workflows/
│       └─ build.yml          ← これから作る CI 定義
├─ Algorithm/PoP/
│   ├─ pop_python/            ← 純 Python SDK
│   │   └─ pyproject.toml
│   └─ pop_rust/              ← Rust バックエンド
│       └─ pyproject.toml
└─ README.md

# ポイント
ディレクトリ	Python パッケージ名	ビルドバックエンド
pop_python	pop-python（例）	setuptools.build_meta
pop_rust	pop-rust（例）	maturin

❷ GitHub Secrets を用意
Secret 名	内容
PYPI_API_TOKEN	PyPI もしくは TestPyPI の API トークン
GH_TOKEN	（オプション）Release アップロード用 Personal Access Token

TestPyPI で動作確認 → OK になったら本番 PyPI 用トークンに入れ替えるのが安全。

❸ .github/workflows/build.yml を作成
name: Build & Publish

on:
  push:
    tags:
      - "v*.*.*"           # v0.1.0 タグを切ったらリリースビルド
  pull_request:
  workflow_dispatch:

jobs:
  # ──────────────────────────────────────────────
  build-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with: { python-version: "3.11" }

      - name: Build pop-python wheel
        run: |
          pip install build
          cd Algorithm/PoP/pop_python
          python -m build --wheel -o ../../dist
      - name: Test (pytest)
        run: |
          pip install ./dist/pop_python-*.whl
          pytest -q Algorithm/PoP/pop_python/test_pop.py

      - uses: actions/upload-artifact@v4
        with:
          name: python-wheel
          path: dist/pop_python-*.whl

  # ──────────────────────────────────────────────
  build-rust:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python-version }}" }

      - name: Build pop-rust wheels (all manylinux targets)
        uses: PyO3/maturin-action@v1
        with:
          args: >-
            build
            --release
            -m Algorithm/PoP/pop_rust/pyproject.toml
            --interpreter python${{ matrix.python-version }}
            --out dist

      - name: Test wheel
        run: |
          pip install dist/pop_rust-*.whl
          pytest -q Algorithm/PoP/pop_rust/tests
      - uses: actions/upload-artifact@v4
        with:
          name: rust-wheels-${{ matrix.python-version }}
          path: dist/*.whl

  # ──────────────────────────────────────────────
  publish:
    needs: [build-python, build-rust]
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - uses: actions/download-artifact@v4
        with: { path: dist }
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@v1.8.11
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
          packages-dir: dist

# 要点
PR / push ではビルド＆テスト → 成功 artifacts を残すだけ。
タグ v*.*.* で走ったときだけ publish ジョブが実行。
maturin-action が自動で manylinux / musllinux wheel を作成。
生成 wheel を TestPyPI に送る場合は
repository-url: https://test.pypi.org/legacy/

❹ リリース手順（開発者がやること）
# (1) バージョンを両側 pyproject.toml で 0.2.0 などに書き換える
git add .
git commit -m "Bump version to 0.2.0"

# (2) タグを切って push
git tag v0.2.0
git push origin main --tags
↑ タグ push に反応して CI が走り、wheel が PyPI / GitHub Release に公開。

❺ 利用者手順
# 純 Python だけ
pip install pop-python

# Rust バックエンド込み（wheel が対応 OS/PyVer にあれば自動）
pip install "pop-python[rust]"
裏側で pop-python が optional-dependencies.rust = ["pop-rust>=0.1.0"] を持つため
extras 指定で pop-rust wheel も合わせて入る。

環境に合う pop-rust wheel が無い場合 → pip は無視して純 Python だけインストール。

❻ よくある質問
Question	Answer
Windows 用の Rust wheel も欲しい	maturin publish -i python3.11 などで Windows マシンからビルドする or GitHub Actions に runs-on: windows-latest を追加。
arm64 / Apple Silicon	cibuildwheel 併用も可だが、maturin-action に manylinux / macos ジョブを増やすだけで OK。
バージョンの同期ミス防止	ルートに version.txt を置き、2 つの pyproject.toml は {{ version }} Jinja テンプレにして hatch / bump-my-version で一括更新する方法が便利。

これで 「ローカル → CI → PyPI 配布 → pip install」 までのフローが完成します。