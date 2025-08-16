# auth_py/logging/test_cloud_logger.py

import os
import sys
import unittest
import uuid
import time
from datetime import datetime

# パス追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from auth_py.logging.cloud_logger import init_log_stream, log_to_cloudwatch

class CloudWatchLoggerTest(unittest.TestCase):

    def setUp(self):
        """最初にロググループ・ストリームを初期化"""
        init_log_stream()
        self.test_uuid = str(uuid.uuid4())

    def test_send_log_success(self):
        """正常なログ送信をテスト"""
        log_data = {
            "event": "test_success",
            "uuid": self.test_uuid,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "This is a test log for success case.",
        }
        try:
            log_to_cloudwatch(log_data)
            print("✅ Success log sent to CloudWatch.")
        except Exception as e:
            self.fail(f"❌ CloudWatch log send failed with exception: {e}")

    def test_send_log_failure(self):
        """意図的に不正なデータを送信して例外発生を確認（構文上は成功する可能性もあり）"""
        bad_data = {
            "event": "test_invalid",
            "uuid": None,  # 一部不正値
            "message": "Invalid test data with None uuid",
        }
        try:
            log_to_cloudwatch(bad_data)
            print("⚠️  Warning: Invalid log sent without exception (may still succeed).")
        except Exception as e:
            print(f"✅ Expected exception occurred: {e}")

    def test_multiple_logs(self):
        """連続送信ができるか確認"""
        for i in range(3):
            log_data = {
                "event": f"batch_{i}",
                "uuid": self.test_uuid,
                "index": i,
                "message": f"Log entry {i}",
            }
            try:
                log_to_cloudwatch(log_data)
                print(f"✅ Sent batch log {i}")
                time.sleep(0.5)  # 過剰送信防止
            except Exception as e:
                self.fail(f"❌ Failed to send batch log {i}: {e}")

if __name__ == "__main__":
    unittest.main()
