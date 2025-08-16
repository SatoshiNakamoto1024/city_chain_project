import pytest
from datetime import datetime
from app import save_journal_entry, update_status, JournalEntry


def test_mongo_operations():
    # 1. サンプル仕訳エントリを作成
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

    # 2. 仕訳エントリの保存
    save_journal_entry(entry)
    # save_journal_entryが正しく動作している場合、MongoDBのjournal_entriesコレクションに
    # txn_123のデータが保存されているはずです。

    # 3. トランザクションのステータス更新
    update_status_data = {
        "transaction_id": "txn_123",
        "new_status": "completed",
        "sender_municipal_id": "city1"
    }
    response = update_status(update_status_data)
    # update_statusはFlaskエンドポイントである場合、requestsでエンドポイントにPOSTするか、
    # あるいはFlaskのtest_clientを使ってエンドポイントを叩くなどの方法が必要です。
    # もし直接関数呼び出しでテストするなら、
    # update_status関数をリファクタしてHTTP依存を排除し、直接DB更新をする関数をテストします。

    assert response.status_code == 200, "Failed to update transaction status"
