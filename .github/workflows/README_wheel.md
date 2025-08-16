# Windowsでは開発しない。Linuxで統一する。
#　サンプルとして、poh_holdmetrics\のwheelを"wheels.yml"にてテスト
ここからは“Windowsではビルドしない／CIで作ったwheelだけ使ってPythonテストを回す”手順を超ていねいにまとめます。
（Rustビルド・DLL地獄はCIに押しつけ、ローカルWindowsは wheel を入れて pytest するだけ）

0) 前提（1分で確認）
Python 3.12 の venv がある（例: D:\city_chain_project\.venv312）

poh_holdmetrics_rust は CI でビルドした wheel が手に入る（後述のCI設定を使うか、既に artifact がある）


#　GitHub Actions と GitHub Desktop のちがい
GitHub Desktop
Git（コミット/プッシュ/プル/ブランチ作成 など）をローカルPCからGUIで操作するアプリ。
👉 例：手元でファイルを編集→GitHubのリポジトリに「プッシュ」するために使う。

GitHub Actions
GitHub が提供する CI/CD（自動実行）サービス。
リポジトリに置いた YAML（ワークフロー）どおりに、GitHub上の仮想マシンでビルド・テスト・配布などを自動実行してくれる。
👉 例：Windows ランナーで Windows用 wheel をビルド→成果物（artifact）をダウンロード可能にする。

要するに：
Desktop は “プッシュする道具”、Actions は “プッシュ後に自動で何かやってくれる仕組み” です。

これからやることの全体像
あなたのリポジトリに Actions の設定ファイル（YAML） を置く
GitHub Desktop で コミット＆プッシュ
GitHub の Actions タブでワークフローを実行（自動 or 手動）
出来上がった wheel（artifact）をダウンロード
ローカル Windows では wheelをインストールするだけ（ビルドしない）

STEP 1: ワークフロー(YAML)を追加
リポジトリのルートにフォルダを作成:
.github/workflows/
その中に wheels-win.yml を新規作成して、次を保存（最小構成のサンプル）：
# .github/workflows/wheels-win.yml
name: build-windows-wheel

on:
  workflow_dispatch:          # 手動実行できる
  push:
    tags: ["v*.*.*"]          # v1.2.3 みたいなタグを push した時にも実行

jobs:
  win-wheel:
    runs-on: windows-latest   # GitHubのWindows仮想マシンで動く
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install maturin
        run: pip install maturin==1.9.3

      - name: Build wheel
        # 下のパスは Rust クレートの Cargo.toml がある場所に合わせて直してください
        working-directory: DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_rust
        run: |
          echo Python: %PythonLocation%
          maturin build --release --features python -o ..\..\..\..\..\dist

      - name: Upload wheel artifact
        uses: actions/upload-artifact@v4
        with:
          name: wheels-win
          path: dist\*.whl
          if-no-files-found: error
        
メモ
working-directory: は Cargo.toml がある rust クレートのディレクトリに合わせて必ず直してください。
-o dist に出した wheel を artifact としてアップロードしています。

STEP 2: GitHub Desktop でコミット＆プッシュ
GitHub Desktop を開く
いま作った .github/workflows/wheels-win.yml が変更として出ていることを確認

・fsmonitor を止めて無効化
cd D:\city_chain_project
git fsmonitor--daemon stop
git config --global core.fsmonitor false
git config core.fsmonitor false

:: 念のためインデックスのフラグもクリア
git update-index --no-fsmonitor

.gitignore を正しく置く
（さっき渡した最新版で OK。msys64/ も入っているか確認）

既にインデックスに乗っている不要物を“管理から外す”
（ファイル自体は消えません。PowerShell で実行推奨）
git add .gitignore
git rm -r --cached msys64
git rm -r --cached mongo-data
git rm -r --cached .venv312
git rm -r --cached DAGs\**\target
git rm -r --cached **\__pycache__
git rm -r --cached **\dist
git rm -r --cached **\build
git rm -r --cached **\*.whl
git rm -r --cached **\*.pyd

状態確認 → コミット → プッシュ
git status
git add -A
git commit -m "ci: add wheel workflows and clean .gitignore; untrack msys64/build artifacts"
git push

# poh_holdmetrics\のような特定のwheelをgithubにプッシュする方法
# クレート一式をステージ
git add DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_rust

# 反映
git commit -m "add poh_holdmetrics_rust crate for CI wheel build"
git push

そして、コミット、プッシュする
git add .github/workflows/build_poh_holdmetrics_rust_wheels.yml
git commit -m "ci: build Windows wheel for poh_holdmetrics_rust via Actions"
git push


下の Summary に例：CI: build wheels on ubuntu/windows と入力
メッセージを書いて Commit to main（ブランチは状況に応じて）
Push origin で GitHub にアップロード

STEP 3: Actions を実行する
GitHub のリポジトリページ → 上部の Actions タブ

左メニューで build-windows-wheel を選択

右側の Run workflow ボタン → Run で手動実行

もしくは v1.2.3 のようなタグを push して自動実行でもOK

緑のチェックになれば成功。失敗ならログを開いてエラー行を見ます。

STEP 4: wheel をダウンロード
実行したワークフローのページの下の方に Artifacts: wheels-win が出ます

クリックして zip をダウンロード

解凍すると dist\poh_holdmetrics_rust-...win_amd64.whl が入っています

STEP 5: Windows ローカルに「インストールだけ」
ローカルでは ビルドしません。wheel を入れるだけ。

bat
Copy
Edit
D:\city_chain_project\.venv312\Scripts\activate

REM 念のため既存を削除
pip uninstall -y poh_holdmetrics_rust

REM DLL事故防止のため、PATHを最小化（任意）
set "OLDPATH=%PATH%"
set "PATH=%VIRTUAL_ENV%\Scripts;%SystemRoot%\System32;%SystemRoot%"

REM ダウンロードした wheel をインストール
pip install D:\path\to\dist\poh_holdmetrics_rust-0.1.0-cp312-*.whl

REM 動作確認
python -X dev -c "import poh_holdmetrics_rust as r; print('OK', hasattr(r,'PyHoldEvent'))"

REM あとはPythonテスト
cd D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python
pytest -vv -s
戻したいとき：

bat
Copy
Edit
set "PATH=%OLDPATH%"
よくある質問
Q. Ubuntuで作った wheel を Windows で使えますか？
A. 使えません。 プラットフォーム毎に別の wheel が必要です。
　→ Windows 用 wheel は Windows ランナーで、Linux 用 wheel は Linux ランナーで作ります。

Q. ローカルでビルドするより楽？
A. はい。ローカルでのビルドやDLL調整は不要になります。CI が毎回クリーンな環境で再現性高く作ってくれます。

Q. Linux/Mac 用も欲しい
A. 同じ YAML に 別ジョブ（runs-on: ubuntu-latest / macos-latest）を増やせばOK。あとでテンプレ出します。

ここまでセットできれば、Windows では wheel を “入れるだけ” で Python テストが回る状態になります。
不安なところ（YAMLのパス、Actions画面のどこを押すか等）、スクショ代わりに文面でもっと細かく案内します。気軽に聞いてください！
