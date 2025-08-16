# DApps側のテストの進め方

# 1.構成要素の分割
まず、Flaskアプリケーション内での重要な部分に分けてテストを進めます。以下の構成に基づいて、各コンポーネントごとにテストを行います。
暗号化と署名：NTRUとDilithiumに関連する暗号化・署名関連の機能。
データベース接続と操作：MongoDBへの接続、データの保存、更新、削除。
トランザクション処理：トランザクションの生成、検証、送信、承認。
エンドポイントテスト：APIエンドポイントが正しく動作しているか、リクエストとレスポンスの確認。

# 2.暗号化と署名のテスト 
まず最初にテストすべきは、NTRU暗号化とDilithium署名に関する部分です。
以下の2つの主要な関数に焦点を当てます：
encrypt_with_ntru：データをNTRUで暗号化します。
generate_signature：Dilithiumで生成された署名を使います。

テスト手順：
暗号化が正しく行われるか確認。
署名が正しく生成され、復号化・署名検証が成功するか確認。

■まずは、Cargoのパスを認識させてテスト環境を整える
$env:PATH="C:\Users\Kibiy\.cargo\bin;" + $env:PATH （VSCODEの場合）
export PATH=/c/Users/Kibiy/.cargo/bin:$PATH (mingw64の場合)

■pythonの場合は仮想化をしてテストする（rustは不要）
※　必要なpip install ... などは仮想化の前に行っておくこと。仮想化ではinstall ×
python -m venv .venv
.\.venv\Scripts\activate （VSCODEの場合）
source .venv/Scripts/activate　（mingw64の場合）

PowerShellでの一時的なPATHの環境変数設定方法　（ターミナルを閉じれば消える）
set コマンドではなく、PowerShell 特有の $env: を使って環境変数を設定してください。
(絶対に　setx ..  は使わないこと。グローバルな設定になるので、環境変数壊れます！)
・コマンド:
$env:PYTHONPATH = $PWD
・確認コマンド:
echo $env:PYTHONPATH
これにより、PYTHONPATH に現在のディレクトリ (D:\city_chain_project\network\DB\mongodb\pymongo) が設定されます。

■rustのmsvcとgnuの互換性の問題が多発
・MSVCに戻す：
rustup target add x86_64-pc-windows-msvc
rustup override set stable-x86_64-pc-windows-msvc
・gnuに戻す：
rustup target add x86_64-pc-windows-gnu
rustup override set stable-x86_64-pc-windows-gnu
・rutstを確認
rustc -vV
・AVX2高度命令を無効化する場合
$env:RUSTFLAGS="-C target-feature=-avx2"
cargo clean
cargo build

・デバッカーを使用してテスト
gdb target/debug/deps/test_ntru_main-9f34c1f65f0f6285.exe
run
backtrace

■.whlファイルのビルド（MSVC版）
・Rust: MSVCツールチェインがセットアップ済み。
・Python環境: 必須ライブラリをインストールします。
python -m pip install setuptools wheel maturin

・以下を実行して.whlファイルをビルドします
maturin build --release --target x86_64-pc-windows-msvc

・ビルドした.whlファイルをPython環境にインストールします。
python -m pip install "target/wheels/ntru_kem-0.1.0-cp312-cp312-mingw_x86_64_msvcrt_gnu.whl" （mingw64の場合）
pip install --force-reinstall target/wheels/ntrust_native_py-0.1.0-cp314-cp314-win_amd64.whl

・PATHを明示的にしてテストする （mingw64の場合）
export PYTHONPATH=$PYTHONPATH:D:/city_chain_project/ntru/ntru-py/.venv/lib/python3.12/site-packages
python -m pytest test_ntru_app.py


def test_ntru_encryption():
    # NTRUの公開鍵と秘密鍵を生成
    ntru_public_key, ntru_private_key = generate_ntru_keys()

    data = "Test Message"
    encrypted_data = encrypt_with_ntru(data, ntru_public_key)

    # 復号化テスト
    decrypted_data = decrypt_transaction_data(encrypted_data, ntru_private_key)
    assert decrypted_data == data, "NTRU decryption failed"

def test_dilithium_signature():
    # Dilithium署名生成
    signature = generate_signature("Test Message", pq_private_key)

    # 署名検証
    is_valid = verify_signature("Test Message", signature, pq_public_key)
    assert is_valid, "Dilithium signature verification failed"

テスト全体の方向性は大筋で正しいように見えます。ただし、以下の点についてはもう少し検討が必要です。

良い点
・テストの構造
pytest を使用してユニットテストを作成しているのは良いアプローチです。
正常系 (test_ntru_encryption) と異常系 (test_ntru_invalid_encryption) の両方をカバーしており、暗号化ライブラリのテストとして基本的な要件を満たしています。

・NTRUの基本的な処理の流れ
公開鍵 (genPublicKey) の生成、設定、取得を行い、その公開鍵を用いて暗号化を試みるという流れは、NTRU暗号の基本的な手順に合致しています。

・気になる点と改善提案
f_new, g_new, d_new の設定
f_new, g_new のようなポリノミアルの選択がかなりシンプルすぎます。NTRUのセキュリティ要件を満たすには、これらのポリノミアルは適切な条件（例えば、f がinvertibleであるなど）を満たす必要があります。
現状では、このポリノミアルの適正性を検証していないため、暗号化処理が動いてもセキュリティ的に弱い可能性があります。
⇒提案:genPublicKey の実装でポリノミアルの正当性をチェックするロジックを追加する。
テストでは、f_new や g_new を適切な関数で生成するようにする。

・公開鍵と秘密鍵の対応
test_ntru_invalid_encryption で異なる Ntru インスタンスを使って暗号化を試みていますが、これが失敗するかどうかの確認はされていません。
現在のコードでは assert encrypted_message is not None しかチェックしていないため、異なる公開鍵を用いた場合にどう挙動が変わるかを検証できていません。
⇒提案:暗号化結果が秘密鍵と一致しないことを確認するテストを追加する。

・encrypt メソッドの挙動
encrypt メソッドの中で、公開鍵や乱数ポリノミアルをどのように利用しているかが不明です。公開鍵設定後の暗号化が本当に機能しているか、復号テストを追加して確認する必要があります。
⇒提案:復号化 (decrypt) テストを追加し、元のメッセージが再現されるか確認する。
暗号化されたデータが、異なる公開鍵では復号できないことも確認する。

・メッセージとポリノミアルのサイズ
メッセージやランダムポリノミアルのサイズがNTRUの設定（N_new, p_new, q_new）と整合性が取れているか確認する必要があります。NTRUのパラメータによって許容されるサイズが異なるためです。
⇒提案:メッセージサイズやポリノミアルの長さがパラメータに準拠していることをテストに含める。

・公開鍵の設定と取得
setPublicKey や getPublicKey を使用していますが、これらのメソッドの挙動がテストされていません。
⇒提案：公開鍵が正しく設定されているか、取得した公開鍵が正しいかをテストで明示する必要があります。

・方向性としての結論
現時点では、全体的に適切な方向性に進んでいると言えます。ただし、次の点を修正・強化することで、より完成度の高いNTRU暗号化モジュールをテストできるようになります：
1.セキュリティを考慮したポリノミアルの選択・検証。
2.公開鍵と秘密鍵の対応を明確に確認するテスト。
3.暗号化と復号の整合性を確認するテスト。
4.メッセージやポリノミアルサイズのパラメータ準拠性の確認。
これらを反映した上で、次のステップとして復号化のテストを追加することをおすすめします。


# 3.データベース操作のテスト 
MongoDBにデータを保存し、更新し、削除するテストを行います。特に、以下の操作に焦点を当てます：
save_journal_entry: 新しい仕訳エントリの保存。
get_mongo_connection: MongoDB接続の検証。
update_status: トランザクションのステータス更新。

テスト手順：
save_journal_entryで新しいエントリがMongoDBに追加されることを確認。
update_statusでトランザクションのステータスが正しく変更されることを確認。

def test_mongo_operations():
    # サンプルの仕訳エントリを作成
    entry = JournalEntry(
        date=datetime.now(),
        sender="user1",
        description="Test Transaction",
        debit_account="愛貨",
        credit_account="愛貨受取",
        amount=100.0,
        judgment_criteria={},
        transaction_id="txn_123"
    )

    # 仕訳エントリの保存
    save_journal_entry(entry)

    # トランザクションのステータス更新
    update_status_data = {
        "transaction_id": "txn_123",
        "new_status": "completed",
        "sender_municipal_id": "city1"
    }
    response = update_status(update_status_data)
    assert response.status_code == 200, "Failed to update transaction status"

# 4.トランザクション処理のテスト 
create_transactionやprocess_transactionなど、トランザクションの生成から承認までの流れをテストします。以下の項目を確認します：

トランザクションが正しく生成され、暗号化され、署名されること。
トランザクションが承認され、データベースに保存されること。
テスト手順：

create_transactionがリクエストを受け、必要なフィールドをチェックし、トランザクションを生成することを確認。
トランザクションがMongoDBに保存され、send_pendingとしてマークされること。

def test_transaction_processing():
    # トランザクションデータを生成
    transaction_data = {
        "sender": "user1",
        "receiver": "user2",
        "amount": 50,
        "sender_municipality": "city1",
        "receiver_municipality": "city2",
        "pq_private_key": "private_key",
        "ntru_public_key": "public_key"
    }

    # トランザクションを送信
    response = send_transaction(transaction_data)
    assert response.status_code == 200, "Transaction creation failed"

    # MongoDBの確認
    transaction = mongo_collection.find_one({"transaction_id": transaction_data['transaction_id']})
    assert transaction is not None, "Transaction not saved in database"

# 5.APIエンドポイントのテスト 
Flaskのエンドポイントが正しく動作するか確認します。例えば、/api/loginや/send_fundsなどが正しく機能するかをチェックします。

テスト手順：
/api/loginエンドポイントでJWTトークンを正常に取得できることを確認。
/send_fundsでトランザクションが正常に送信されることを確認。

def test_login():
    data = {"username": "user1", "password": "password123"}
    response = client.post('/api/login', json=data)
    assert response.status_code == 200, "Login failed"
    assert 'token' in response.json, "Token not returned"

def test_send_funds():
    data = {
        "sender_id": "user1",
        "receiver_id": "user2",
        "amount": 50
    }
    response = client.post('/send_funds', json=data)
    assert response.status_code == 200, "Send funds failed"

# テスト実行順
暗号化・署名のテスト
データベース操作のテスト
トランザクション処理のテスト
APIエンドポイントのテスト
これらのテストを順番に実行していくことで、アプリケーション全体の動作を確認できます。最初に暗号化と署名のテストから始め、その後データベース操作、トランザクション処理、最後にAPIエンドポイントのテストを行いましょう。


# immuDBにDApps側のapp.pyからトランザクションを保存するテスト
1. venv 作成時の "Operation not permitted" エラー
これは、WSL2 (Windows Subsystem for Linux) で D: ドライブ上のフォルダーに仮想環境を作ろうとしている ため、Windowsのファイルシステムの制限によって権限エラーが発生している可能性が高い。

💡 対処法:
WSL内のLinuxファイルシステム (/home/satoshi/) に venv を作る！
シンボリックリンクを使って py_immu/venv をWSL内に置く
# WSLの自分のホームディレクトリに移動
cd ~
mkdir py_immu_venv

# D:ドライブの `py_immu/` に仮想環境へのシンボリックリンクを作成
ln -s ~/py_immu_venv /mnt/d/city_chain_project/network/DB/immudb/py_immu/venv

# もう一度仮想環境を作成
python3 -m venv ~/py_immu_venv

# 仮想環境を有効化
source ~/py_immu_venv/bin/activate


# rust側のimmuDBの起動・テスト
2️⃣ Rust 側のテストを行うための環境セットアップ
✅ Rust 側の immudb_service のコードを実行する前に、プロジェクトディレクトリ へ移動し、環境を整える。

➡ 手順：
# Rust プロジェクトのディレクトリへ移動
cd /mnt/d/city_chain_project/network/DB/immudb/rs_immu

# Rust のバージョンを確認（`cargo` が利用可能かチェック）
rustc --version
cargo --version
想定される出力例：

scss
Copy
Edit
rustc 1.76.0 (f00182c 2024-01-12)
cargo 1.76.0 (a442d2f 2024-01-13)
3️⃣ Rust の gRPC コード生成
✅ immudb.proto から gRPC の Rust 用コードを自動生成する。

➡ 手順：

bash
Copy
Edit
cargo build
この処理により、以下の内容が生成される：

target/debug/ にバイナリファイルが作成される
src/immudb.rs に gRPC の Rust 定義が生成される
4️⃣ Rust の本番実装（メインチェーン）を実行
✅ main_immudb.rs（本番用）を実行し、Rust から immuDB への書き込み・読み出しをテスト。

➡ 手順：
cargo run --bin main_immudb

期待される出力：
[2025-02-11 15:00:00] INFO Logged in successfully. Token: ...
[2025-02-11 15:00:01] INFO Main chain data stored for key: main_chain_data
[2025-02-11 15:00:02] INFO Main chain data retrieved for key main_chain_data: This is main chain block data
✅ ここまでで Rust の immuDB への本番データの保存・取得が成功！

5️⃣ Rust 側のテストコードを実行
✅ test_immudb.rs を実行し、Rust から immuDB へのテストデータ保存・取得が正常に動作するかを確認。

➡ 手順：

bash
Copy
Edit
cargo test -- --nocapture
期待される出力：

bash
Copy
Edit
running 1 test
[2025-02-11 15:05:00] INFO Retrieved value for test_key: Hello, immuDB!
✅ immuDB の書き込み・読み出しテストに成功しました。
test test_immudb_set_get ... ok
まとめ
✅ Rust 側の immuDB 本番実装 (cargo run --bin main_immudb) 成功！
✅ Rust 側のテスト (cargo test -- --nocapture) 成功！

これで、Rust 側の immuDB 連携も Python 側と同じように動作することが確認できました！ 🚀