
これで “先頭に表示される” パスが、D:\city_chain_project\Strawberry\perl\bin\perl.exe になっていればOKです。
もし C:\msys64\usr\bin\perl.exe や他の MSYS2 パスが先に来ているなら、Strawberry Perl が使われていません。

2. PATH の優先順を入れ替える
もし MSYS2 の Perl が先に来ている場合は、Strawberry の bin を前に出してください。


D:\city_chain_project\openssl-src-rs\rust-openssl\ を利用
そのために、下記をやる必要がある。 
# 1) 現在の PATH を分割して msys64 を除外
$paths = $env:PATH -split ';'
$filtered = $paths | Where-Object { $_ -notmatch 'msys64' }

# 2) Strawberry の nasm と perl、そして Rust の .cargo\bin を先頭に
$newPrefix = @(
  "$env:USERPROFILE\.cargo\bin",
  'D:\city_chain_project\Strawberry\c\bin',
  'D:\city_chain_project\Strawberry\perl\bin'
)

# 3) 再構築して環境変数にセット
$env:PATH = ($newPrefix + $filtered) -join ';'


#　Cargo build が通る方法
以下の手順で「x64 Native Tools Command Prompt for VS 2022」を起動し、MSVC のコンパイラや nmake を使えるようにします。なお、事前に「Visual Studio Build Tools」（または Visual Studio 本体）に「C++ によるデスクトップ開発」ワークロードがインストールされている必要があります。

1. Visual Studio Build Tools のインストール確認
Windows の「スタート」メニューを開き、「Visual Studio Installer」と入力して起動。
インストール済みの「Visual Studio Build Tools」または「Visual Studio 2022」に対して、「変更」 をクリック。
「ワークロード」タブ内の**「C++ によるデスクトップ開発」**がチェックされているか確認。
チェックされていなければ付けて、右下の「変更」→インストールを実行。
完了したら Installer を閉じる。

2. 「x64 Native Tools Command Prompt for VS 2022」を起動
スタートメニューを開く
**「x64 Native Tools Command Prompt for VS 2022」**と入力
表示された候補をクリックして起動
もし見つからなければ「Developer Command Prompt for VS 2022」と検索し、リストから「(x64)」を含むものを選んでください

必要なら 右クリック → 「管理者として実行」
ファイルシステムやレジストリへの書き込みがあるビルド時に管理者権限が必要になる場合があります
このプロンプトが開くと、自動的に以下の環境変数が設定されます。
PATH に cl.exe／link.exe／nmake.exe のあるディレクトリが追加
INCLUDE に MSVC の include フォルダが設定
LIB に MSVC の lib フォルダが設定
まず以下を実行してみましょう。
> cl           ← Microsoft C/C++ コンパイラのバージョン情報が出れば OK
> nmake        ← nmake のヘルプが出れば OK
> where perl   ← Strawberry Perl のパスが先頭に来ていれば OK
> where nasm   ← Strawberry nasm のパスが先頭に来ていれば OK

3. OpenSSL 
まずは、下記のフォルダーへカレントを移動し、buildを実行
D:\city_chain_project\openssl-src-rs>cd openssl-3.4.0

D:\city_chain_project\openssl-src-rs\openssl-3.4.0>perl -Iutil\perl Configure VC-WIN64A no-shared no-tests no-comp no-ssl3 no-zlib --prefix=D:\city_chain_project\openssl-src-rs\openssl-build

Locale 'Japanese_Japan.932' is unsupported, and may crash the interpreter.
Configuring OpenSSL version 3.4.0 for target VC-WIN64A
Using os-specific seed configuration
Created configdata.pm
Running configdata.pm
Locale 'Japanese_Japan.932' is unsupported, and may crash the interpreter.
Created makefile.in
Created makefile
Created include\openssl\configuration.h

**********************************************************************
***                                                                ***
***   OpenSSL has been successfully configured                     ***
***                                                                ***
***   If you encounter a problem while building, please open an    ***
***   issue on GitHub <https://github.com/openssl/openssl/issues>  ***
***   and include the output from the following command:           ***
***                                                                ***
***       perl configdata.pm --dump                                ***
***                                                                ***
***   (If you are new to OpenSSL, you might want to consult the    ***
***   'Troubleshooting' section in the INSTALL.md file first)      ***
***                                                                ***
**********************************************************************

✅ 次のステップ：ビルドとインストール
1️⃣ nmake でビルドを開始（Visual Studio x64 Native Tools Command Prompt で実行）
nmake

⏳ 今なにをしてるの？
nmake の間は：
crypto/*.c や ssl/*.c のファイルを .obj にコンパイル中
最終的に .lib をリンクして生成中（静的ライブラリ）
ビルドログに cl.exe（Cコンパイラ）や ml64.exe（アセンブラ）が表示されているはずです

✅ 完了時の目印
Generating 'libcrypto.lib'
Generating 'libssl.lib'
と出れば成功直前です！
そのあと nmake install を実行することで openssl-build/ にインストールされます。

2️⃣ ビルド成功後、インストール
nmake install

⚠ 必ず Visual Studio Developer Command Prompt で実行してください（普通の PowerShell や cmd.exe ではなく）
例えば「x64 Native Tools Command Prompt for VS 2022」


このあと、
> dir D:\city_chain_project\openssl-src-rs\openssl-build\lib
> dir D:\city_chain_project\openssl-src-rs\openssl-build\include\openssl
で .lib とヘッダが生成されていることを確認してください。

4. Rust モジュールのビルド
同じプロンプト上で、Rust 側のディレクトリへ移動してビルドします。
> cd /d D:\city_chain_project\Algorithm\VRF\vrf_rust_src
# ② 正しいビルド成果物を指す
$env:OPENSSL_DIR         = "D:\city_chain_project\openssl-src-rs\openssl-build"
$env:OPENSSL_LIB_DIR     = "D:\city_chain_project\openssl-src-rs\openssl-build\lib"
$env:OPENSSL_INCLUDE_DIR = "D:\city_chain_project\openssl-src-rs\openssl-build\include"

> cargo clean
> cargo build --release
これで、openssl-sys はビルド済みのライブラリを見つけて正常にリンクできるはずです。


# cargo test 
対処法①：Python のインストール先を PATH に追加する
Python の DLL があるフォルダ（例：C:\Users\kibiy\AppData\Local\Programs\Python\Python312）を探す
python.exe と同じフォルダに python3.dll があるはずです。

PowerShell で、テストを実行する前にパスを通す
# あなたの実際の Python インストール先に置き換えてください
$env:PYO3_PYTHON = "D:\Python\Python312\python.exe"

cd D:\city_chain_project\Algorithm\VRF\vrf_rust_src
cargo clean
cargo test

   Compiling vrf_rust v0.1.0 (D:\city_chain_project\Algorithm\VRF\vrf_rust_src)
    Finished `test` profile [unoptimized + debuginfo] target(s) in 44.43s
     Running tests\test_vrf.rs (target\debug\deps\test_vrf-2f5991304cd199ff.exe)

running 2 tests
test test_vrf_bad_proof ... ok
test test_vrf_roundtrip ... ok

test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.07s


# pythonとの通信に備え、maturin build --release -o dist
そのためにも、まずは仮想上（.venv312）にはいる。
そして、一時的に先にパスをセットしておく。
rem ── 一時的（そのプロンプト内だけ）に設定 ─────────────────────────
set OPENSSL_DIR=D:\city_chain_project\openssl-src-rs\openssl-build
set OPENSSL_LIB_DIR=D:\city_chain_project\openssl-src-rs\openssl-build\lib
set OPENSSL_INCLUDE_DIR=D:\city_chain_project\openssl-src-rs\openssl-build\include

(.venv312) D:\city_chain_project\Algorithm\VRF\vrf_rust_src>maturin develop --release
をやってPyO3に備えておく。

そして、dist\ に.whlを配布物を吐き出すために下記をやる。
(.venv312) D:\city_chain_project\Algorithm\VRF\vrf_rust_src>maturin build --release -o dist
🔗 Found pyo3 bindings
🐍 Found CPython 3.12 at D:\city_chain_project\.venv312\Scripts\python.exe
   Compiling openssl-sys v0.9.109
   Compiling openssl-macros v0.1.1
   Compiling pyo3-ffi v0.18.3
   Compiling pyo3 v0.18.3
   Compiling pyo3-macros-backend v0.18.3
   Compiling thiserror-impl v2.0.12
   Compiling openssl v0.10.73
   Compiling thiserror v2.0.12
   Compiling pyo3-macros v0.18.3
   Compiling vrf v0.2.5
   Compiling vrf_rust v0.1.0 (D:\city_chain_project\Algorithm\VRF\vrf_rust_src)
    Finished `release` profile [optimized] target(s) in 39.60s
📦 Built wheel for CPython 3.12 to dist\vrf_rust-0.1.0-cp312-cp312-win_amd64.whl