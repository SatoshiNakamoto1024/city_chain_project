■　実験0
“rvh_trace” と “poh_metrics” をまず ローカル環境だけで動かす 手順
（Docker／GitHub Actions は後段で）

/ビルド → インポート確認
# ルート直下で
DOCKER_BUILDKIT=1 docker compose build --no-cache --progress=plain

# runtime で import OK を確認
docker compose run --rm app
import OK: True 的な表示が出れば、wheel とラッパのインストールは成功です。




0. 前提ディレクトリ例
DAGs\
└─ libs\
   └─ algorithm\
      ├─ rvh_trace\
      │   ├─ rust\Cargo.toml          # ← crate-type="cdylib"
      │   └─ python\tests\...
      └─ poh_holdmetrics\
          ├─ rust\Cargo.toml
          └─ python\tests\...
両方ともユニットテストは通る ところまで出来ているとします。

#　1. WSL のセットアップ
/ 4.24.4 ソースを C 拡張スキップ でビルド
pip uninstall -y protobuf
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
pip install protobuf==5.27.0
REM ↑ 変数のおかげでランタイムでは純 Python 実装のみロードされる
手元で wheel をビルドしないので Visual C++ エラーは出ない

WSL の有効化
管理者 PowerShell を開き、以下を実行：
PS C:\WINDOWS\system32> wsl --install

これで既定のディストリビューション（Ubuntu）がインストールされ、再起動後にユーザー設定（UNIX ユーザー名／パスワード）を求められます。

Ubuntu の起動
スタートメニューから「Ubuntu」を起動。
sudo apt update && sudo apt upgrade -y
PW: greg1024

(よく切れるので、切れたらこれをやる)
# 1) ビジーでも強制的にアンマウント
deactivate          # venv を抜ける
sudo umount -l /mnt/d      # ← l (エル) オプション
# 2) 改めて Windows の D: をマウント
sudo mount -t drvfs D: /mnt/d -o metadata,uid=$(id -u),gid=$(id -g)

Python3.12 のインストール
Ubuntu のリポジトリによっては最新が入っていないので、deadsnakes PPA を追加しておくと便利です：
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv
sudo apt install python3.12 python3.12-dev python3.12-venv
sudo apt install python3-distutils
python -m pip install nox    

python3.12 コマンドで起動できるようになります。

pip と仮想環境の準備
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.12
python3.12 -m venv ~/envs/linux-dev
source ~/envs/linux-dev/bin/activate

2. プロジェクトをクローン／マウント
Windows 上のソースコードディレクトリ
たとえば D:\city_chain_project\DAGs\libs\algorithm\ 配下にあるなら、WSL 側からは
/mnt/d/city_chain_project/DAGs/libs/algorithm/ でアクセスできます。
下記のようになればOK
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project$

# 0) 共有ライブラリを持つシステム Python を明示
export PYO3_PYTHON=/usr/bin/python3.12     # ← ここを固定

# 子クレートに追加必須！
■　Cargo.toml
これを書くだけで pyo3-build-config が自動でリンクフラグを伝搬
[package.metadata.pyo3]
extension-module = true

. そもそも “abi3” とは？
用語	正式名称	ざっくり説明
ABI	Application Binary Interface	バイナリ同士の取り決め（関数呼び出し規約・シンボル名など）。
Stable ABI (= abi3)	PEP 384 で導入された Python3 系の “壊さない約束” を守る公開 API 群。
3.2 以降の CPython に存在し、後方互換が保証される。

A. abi3-py312
選択肢、	　　　　Wheel タグ、	依存する libpython、	対応ランタイム、	配布コスト、	将来のマイナーバージョン UP
(現在の固定方針)、	abi3-py312、	必須（3.12）、　	“3.12 以上” の CPython に限定、　	1 ファイルで済む	3.13 や 3.14 が出ても動く

なぜこれで“本番実装向け”になるのか？
ポイント	効果
Rust 1.88.0 に固定 (MSRV)	将来の Rust 更新で突然壊れない
Python 3.12 ヘッダ & abi3‑py312	ビルドは 3.12 だけ で済み、Wheel は 3.12 以上なら全バージョン共通
pyo3_build_config を build.rs で呼ぶ	OS ごとの libpython 探索を自動化 → “リンクエラー地獄” 回避
maturin 1.5 系 + --compatibility abi3	多プラットフォームで同一 wheel 名（‑abi3‑*）が生成出来る
matrix でクレート拡張	新しい Rust crate が増えても 1 行追加するだけ

abi3 って？
CPython が提供する「後方互換を保証する C API の縮小セット」です。
abi3‑py312 の wheelは「Python 3.12 以降はずっと同じバイナリで動く」という意味なので、将来 3.13 / 3.14 が出てもビルドをやり直す必要がありません。

これで CI は “Rust テスト + Wheel 出力” を 1 ジョブで完結し、生成された wheel をそのまま本番（PyPI や内部アートファクトリ）へ流し込めます。


解決方針：feature を分ける ―― “ライブラリ用” と “拡張モジュール用”
# ───── DAGs/libs/algorithm/rvh_trace/rvh_trace_rust/Cargo.toml ─────
[dependencies]
pyo3 = { workspace = true, default-features = false }   # ①一旦 feature を全部外す
pyo3-async-runtimes = { workspace = true }

[features]
# デフォルト = 普通の Rust ライブラリ（→ cargo test 用）
default = ["pyo3/auto-initialize"]   # ← libpython をリンクする安全パス

# Python 拡張を作るときだけ明示的に指定
py-ext = ["pyo3/extension-module", "pyo3/abi3-py312"]

ポイント
auto‑initialize … Rust 側から Python を呼ぶテストが勝手に Py_Initialize() してくれる &
共有ライブラリもリンクしてくれる（未定義シンボルが解消）。
py-ext … Wheel を作るときしか使わない。こちらは “リンクしない” 拡張用。

build.rs はそのままで OK
pyo3_build_config::add_extension_module_link_args() は
cfg!(pyo3_extension_module) が立っている時 (= py‑ext 指定時) だけ発火するので、
デフォルトビルドでは余計なフラグを出さない。



STEP 1️⃣ workspace にメンバー登録
D:\city_chain_project\Cargo.toml
[workspace]
resolver = "2"
members = [
    "DAGs/libs/algorithm/rvh_trace/rust",
    "DAGs/libs/algorithm/poh_holdmetrics/rust",
    # 既存:
    "DAGs/rust/*",
]
すでに DAGs/rust/* で “上位” フォルダを拾えていれば追加不要ですが、
一発で確実に拾いたいなら個別に書く のが安全です。

STEP 2️⃣ Rust だけビルド & テスト
# ルートで
/ 動作確認コマンド
・ Windows
cargo clean
cargo build -p rvh_trace_rust --release
cargo test -p rvh_trace_rust --release
cargo test -p poh_holdmetrics_rust --release

・ Linux (WSL)
cd /mnt/d/city_chain_project
cargo build -p rvh_trace_rust --release
cargo test -p rvh_trace_rust --release
cargo test -p poh_holdmetrics_rust --release

/ nox 一括テスト
※　各ディレクトリの〇〇_integration.pyの冒頭にこれを埋め込んでおくこと。捜索で引っかかるようになる。
import pytest
pytestmark = pytest.mark.ffi

そして、noxのコードにディレクトリ追加して、テスト対象範囲を増やしてから、
nox -s all

を行う。
これで得られる挙動
| セッション     | Rust 単体        | PyO3 実装テスト                   | Python ラッパ | **統合テスト** |
| ------------- | --------------　 | -------------------------------  | ----------   | ---------      |
| **win\_host** | ✅ `cargo test` | ✅ (`tests/test_py_bindings.rs`) | ―            | ―              |
| **win\_py**   | ―           　   | ✅ wheel インポート               | ✅          | ✅            |
| **wsl\_rust** | ✅              | ✅                               | ―            | ―             |
| **wsl\_py**   | ―           　   | ✅ wheel インポート               | ✅          | ✅            |

注 : 統合テストは Python 側から Rust 拡張を import するので
Rust ビルド後（maturin develop --features py-ext）のセッションで走らせています。


# errorが起こるパターン
原因1　何が起きているか ―― テスト・スクリプト側のパス解決ミス
Failed to spawn Command … "/home/satoshi/envs/linux-dev/Scripts/python.exe" : No such file or directory
rvh_trace_rust 本体も bindings.rs もコンパイルもテストも全部 OK
(cargo test で 0 テスト成功 → 失敗は external Python 呼び出しだけ)
こけているのは tests/test_import.rs が Windows 固定の exe パス
VIRTUAL_ENV/Scripts/python.exe を組み立ててしまい、
Linux / WSL / CI では存在しないので ENOENT が返っているだけ。
ライブラリや PyO3 の問題ではありません。

修正ポイント：テストの Python 実行ファイルを OS 別に探す
diff --git a/tests/test_import.rs b/tests/test_import.rs
@@
-    let python = PathBuf::from(&venv).join("Scripts/python.exe");
+    let python = if cfg!(windows) {
+        PathBuf::from(&venv).join("Scripts/python.exe")
+    } else {
+        // Linux/macOS は bin/python または bin/python3
+        let cand = ["bin/python", "bin/python3"];
+        cand.iter()
+            .map(|p| PathBuf::from(&venv).join(p))
+            .find(|p| p.exists())
+            .expect("python executable not found in venv")
+    };

項目	実際の原因	修正
リンクエラー	既に解決済み（feature 分離）	—
今回の失敗	test_import.rs が Windows 固定パスで python.exe を呼ぼうとして OS 依存 ⇒ ENOENT	上記のように OS ごとに bin/python / Scripts/python.exe を分岐、または which python3 を使う

テストコードを直せば test_python_import_only も通り、CI 全緑 になります。


原因2 ―― find_cdylib() が Linux 系のファイル名を想定していない
Linux／macOS で cdylib をビルドすると
target/debug/deps/ に出るファイル名は
librvh_trace_rust-<hash>.so   (例: librvh_trace_rust-3f10a0e84f0e6a31.so)
先頭に lib が付く
後ろに ハッシュ付きのサフィックス が付く
tests/test_py_bindings.rs の find_cdylib() は
if p.file_stem().and_then(|s| s.to_str()) == Some("rvh_trace_rust")
と 完全一致 させているため、
librvh_trace_rust-… を一つも拾えず panic → テスト失敗。

Windows だけで確認していたときは
rvh_trace_rust.dll がそのまま生成されるので通っていただけ、というわけです。

直し方（最短パッチ）
diff --git a/tests/test_py_bindings.rs b/tests/test_py_bindings.rs
@@
-                if p.file_stem().and_then(|s| s.to_str()) == Some("rvh_trace_rust")
-                    && p.extension().and_then(|e| e.to_str()) == Some(DYLIB_EXT)
-                {
-                    return p;
-                }
+                if p.extension().and_then(|e| e.to_str()) == Some(DYLIB_EXT) {
+                    //   Windows : rvh_trace_rust.dll
+                    //   macOS   : librvh_trace_rust-<hash>.dylib
+                    //   Linux   : librvh_trace_rust-<hash>.so
+                    let stem = p.file_stem().and_then(|s| s.to_str()).unwrap_or("");
+                    if stem.ends_with("rvh_trace_rust") || stem.contains("rvh_trace_rust-") {
+                        return p;
+                    }
+                }

ends_with("rvh_trace_rust") で Windows の素直な DLL 名をカバー
contains("rvh_trace_rust-") で -<hash> 付きの Unix 系をカバー


原因3ー今度のエラーの正体
ライブラリは見つかったが Python がインポートできない
find_cdylib() で拾えたのは
librvh_trace_rust‑xxxxxxxx.so   （← cdylib のデフォルト名）
先頭 lib ＋ハッシュ付きのファイル。
Python の import ルールは モジュール名＝ファイル名 なので
import rvh_trace_rust → …/rvh_trace_rust*.so を探します。
lib 付きはスルーされるため ModuleNotFoundError が起きる。
Windows では DLL→PYD にコピーしていたので偶然動いていましたが、
Linux/macOS では “lib” を取り除いた別名を置く必要があります。

テスト側の最小修正
ensure_pyd()（≒Unix 版）で シンボリックリンクかコピー を置くだけです。
@@
 #[cfg(not(target_os = "windows"))]
 fn ensure_pyd(src: &Path) -> PathBuf {
-    src.to_path_buf()
+    // 例: librvh_trace_rust‑abcd.so  →  rvh_trace_rust.so
+    let dst = src.with_file_name("rvh_trace_rust.so");
+    if !dst.exists() {
+        // ハードリンクでも OK。書き込み権限が無ければ std::os::unix::fs::symlink を使う
+        std::fs::copy(src, &dst).expect("lib→so copy failed");
+    }
+    dst
 }

ポイントは rvh_trace_rust.so という素直な名前を置くこと。
Python は EXTENSION_SUFFIXES の中に単純「.so」も含むので
これだけで import rvh_trace_rust が通ります。
_symlink を張れる環境なら std::os::unix::fs::symlink(src, &dst) の方が速いです。

これで通る理由
find_cdylib() は相変わらず lib付き を拾う。
ensure_pyd() が rvh_trace_rust.so を同じディレクトリに作成。
テストはそのディレクトリを PYTHONPATH へ追加。
import rvh_trace_rust → 拡張モジュールが見つかる。
CI でもローカルでも test_python_module が PASS になるはずです。

# 状況	方法
.so（linux）, .pyd(windows)が必要になるので、該当クレートまでカレントで行き作成する！
手動テスト	.dll → .pyd または .so にリネーム＆コピーでOK
開発中の自動環境 (CI, Docker)	maturin develop --release を使えば .pyd/.so が適切に生成され、Pythonからインポート可能
本番デプロイ用	maturin build --release --compatibility abi3 で .whl を生成して pip install

OS	Pythonが読み込めるファイル	名前に必要な変換
Windows	.pyd	rvh_trace_rust.dll → rvh_trace_rust.pyd
(.pyd ファイルは .dllと同じところに rvh_trace_rust.pyd としてありますか？)
Linux/macOS	.so	librvh_trace_rust-abcxyz.so → rvh_trace_rust.so
(.so ファイルは tests/ ディレクトリ直下に rvh_trace_rust.so としてありますか？)
これでどのプラットフォームでも Python テストが安定します。

✅ 修正：sys.path.insert() を .pyd の場所に対しても追加する
あなたのコードのこの部分：
let code = CString::new(format!(
    "import sys; \
     sys.path.insert(0, r\"{}\"); \
     sys.path.insert(0, r\"{}\"); \
     sys.path.insert(0, r\"{}\")",
    lib_dir.display(),
    dlls_dir.display(),
    python_home
)).expect("CString::new");
...

// 1.3) ビルド済み cdylib/.pyd を見つけて PYTHONPATH に追加
let cdylib = find_cdylib();
let pyd = ensure_pyd(&cdylib);
add_pythonpath(pyd.parent().unwrap());

// このように `with_gil` の中に移動して表示させる
// ── 追 加 ────────────────────────────────
// いま動いている Python にも同じディレクトリを挿入する
{
    let sys     = py.import("sys")?;
    use pyo3::types::PyList;
    let sys_path = sys
        .getattr("path")?
        .downcast_into::<PyList>()?;

    let dir_str = pyd
        .parent()
        .unwrap()
        .to_str()
        .expect("utf‑8");

    if !sys_path.iter().any(|o| o.extract::<&str>().map_or(false, |s| s == dir_str)) {
        sys_path.insert(0, dir_str)?;
    }
}

println!(
    " PYTHONPATH に追加済み: {}",
    pyd.parent().unwrap().display()
);

# rust側のテストOK
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.14s

   Doc-tests rvh_trace_rust

running 1 test
test DAGs/libs/algorithm/rvh_trace/rvh_trace_rust/src/lib.rs - (line 6) - compile ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.99s



STEP 3️⃣ PyO3 バインディングを “仮想環境” にインストール
# 初回だけ
py -3.12 -m venv .venv312
.venv312\Scripts\activate     # bashなら source .venv312/bin/activate
pip install -U maturin pytest

# rvh_trace
maturin develop -m DAGs/libs/algorithm/rvh_trace/rvh_trace_rust/Cargo.toml --release
python -c "import rvh_trace; print(rvh_trace.__doc__[:60])"

# poh_holdmetrics
maturin develop -m DAGs/libs/algorithm/poh_holdmetrics/rvh_holdmetrics_rust/Cargo.toml --release
python -c "import poh_holdmetrics, inspect, textwrap, sys; print('OK')" 

STEP 4️⃣ Python ユニット／FFI テスト
pytest DAGs/libs/algorithm/rvh_trace/rvh_trace_python/rvh_trace/tests -q
pytest DAGs/libs/algorithm/poh_holdmetrics/rvh_holdmetrics_python/rvh_holdmetrics/tests -q
通過 すれば「Rust ↔ Py」の結合も完了。

STEP 5️⃣ “nox 一括” で 4 セッション確認
noxfile.py に対象クレート名を追加
CRATES = ["bridge_s1", "bridge_s2", "rvh_trace", "poh_holdmetrics"]
（※ rvh_trace 側で crate-type="cdylib" ならそのまま。
Rust‑only クレートなら CRATES へ入れなくても OK）

実行
nox -s all
WinHost → WinPy → WSL‑Rust → WSL‑Py の全ビルドが順で走り、
完走すれば「Windows & WSL」両方で動作保証 が取れます。

STEP 6️⃣ Docker で“本番相当”ランタイムを試す
(まだ Dockerfile が無ければ)
docker/Dockerfile.dev 例
FROM rust:1.88-slim AS build

WORKDIR /app
COPY . .
RUN cargo build --workspace --release

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /app/target/release/librvh_trace.so /usr/local/lib/
COPY --from=build /app/target/release/libpoh_holdmetrics.so /usr/local/lib/
COPY DAGs/libs/algorithm/rvh_trace/python /app/rvh_trace
COPY DAGs/libs/algorithm/poh_metrics/python /app/poh_holdmetrics
RUN pip install pytest orjson
CMD ["pytest", "-q"]

・powershell
docker build -f docker/Dockerfile.dev -t dag_algo_test .
docker run --rm dag_algo_test
→ コンテナで pytest がパスすれば「CI 上の Linux イメージでも動く」ことを確認。

STEP 7️⃣ GitHub リポジトリ初 push（任意）
.github/workflows/ci.yml に
jobs:
  build:
    strategy:
      matrix: { os: [windows-2022, ubuntu-22.04] }
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@1.78.0
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install nox maturin
      - run: nox -s all
git add . ; git commit -m "feat: add rvh_trace & poh_metrics"; git push origin main

“どこから始める？” まとめ
やること	コマンド	ゴール
1. ワークスペース登録	edit Cargo.toml	members にパス追加
2. Rust テスト	cargo test -p rvh_trace	ビルド確認
3. PyO3 install	maturin develop -m <Cargo.toml>	.pyd/.so 生成
4. Python テスト	pytest <tests>	FFI 結合 OK
5. nox all	nox -s all	Win+WSL 4 通りパス
6. Docker	docker build/run	本番相当 Linux でパス
7. GitHub CI	git push	Actions が green

まずは STEP 1 → 4 をローカルで回すだけで
「ふたつのアルゴリズムクレートが新ルート構成でも動く」ことを確認できます。


STEP 7️⃣ dockerによるビルド
1.1 これで何が出来る？
ターゲット	用途	サイズ参考*
build stage	開発 & CI: ビルド／テスト	~2 GB
runtime stage	本番: wheel だけ実行	<100 MB

* Rust + LLVM を含むので builder はどうしても重め。
最終イメージは Python slim + abi3 wheel だけなのでかなり小さくなります。

2. ビルド／テスト／実行のコマンド
# 2‑1. 開発 / CI 用 builder イメージ
docker build --target build  -t citychain-builder  .

# 2‑2. （オプション）中に入って手動デバッグ
■　WSL / Git‑Bash / Linux
docker run --rm -it \
  -v ${PWD}:/workspace \
  citychain-builder bash

■　PowerShell
docker run --rm -it `
  -v "${PWD}:/workspace" `
  citychain-builder bash

■　cmd
docker run --rm -it -v "%cd%:/workspace" citychain-builder bash

# 2‑3. 本番ランタイムイメージ
docker build --target runtime -t rvh-trace-runtime .

# 2‑4. ひとこと動作確認
docker run --rm rvh-trace-runtime

 → "import OK → 0.1.0" が出れば成功
   Windows + Docker Desktop での volume マウント


3. docker‑compose でまとめたい場合
# compose.yaml
services:
  dev:
    build:
      context: .
      target: build      # ← builder stage
    volumes:
      - .:/workspace
    command: bash        # そのままシェルで入る

  app:
    build:
      context: .
      target: runtime    # ← runtime stage

5‑2. compose で一発
# 開発シェル (builder stage に入る)
docker compose -f docker/compose.yaml run --rm dev

# 本番イメージをビルドして起動
docker compose -f docker/compose.yaml run --rm app
# -> "import OK -> 0.1.0" が表示

4. よくあるハマりポイント
症状	原因	対処
python3.12-dev が見つからない	ベースが Debian 11/12 などの古いイメージ	ubuntu:24.04 や debian:trixie など 3.12 が入るものを使う
maturin develop で glibc 違いエラー	manylinux ベースと混在	ローカル開発なら ubuntu ベースで統一 or docker run --platform を揃える
nox が見つからない	まだ pip install nox していない	builder stageのように RUN pip install nox する

5. まとめ
Dockerfile をルートに置く（上記コピペで OK）
docker build で builder → テストが全部通る
同じ Dockerfile から runtime ステージだけ切り出せば、本番は wheel だけ載せた軽量イメージ
開発中は docker compose or volume 共有でソースを編集 → cargo test / pytest / nox を回す
これで Windows／WSL／macOS どこでも “環境差ゼロ” で動きます 🎉

「まずはローカルで pip install -e '.[dev]' ＋ nox -s all を回しておいて、
動いたら 同じ手順を Docker に閉じ込める」——という流れだとハマりが少ないです。


# Docker エラー対処法
■　maturin が落ちている直接の原因は パスではなく
「pyproject.toml に readme = "../README.md" が残っているのに その README.md を
コンテナにコピーしていない」 ことです。

ローカル環境ではプロジェクト直下に README があるため問題なく、
Docker ビルドでは .dockerignore と COPY の最小コピー方針で README を除外したため
ファイルが無くなり、すべての nox サブセッション（maturin develop を呼ぶ）が失敗します。

解決パターン
| 方法                              | メリット                  | デメリット                 |
| --------------------------------- | ------------------------ | ------------------------- |
| **A. README を pyproject から外す**
<br>`readme` 行を削除（コメントアウト）| *最もシンプル。Dockerfile も `.dockerignore` も触らない* | PyPI へ公開するときに長い説明文が載らなくなる |
| **B. README をコンテナへコピー**<br>Dockerfile と `.dockerignore` に 1 行追加 | PyPI 用 README を保持したままビルド可                   | ほんの数 kB とはいえイメージにファイルが増える |


# docker で単体テストもできる
docker compose build
docker compose run --rm test_rvh_trace       # rvh_trace の Python テスト
docker compose run --rm test_poh_holdmetrics   # poh_holdmetrics の Python テスト
