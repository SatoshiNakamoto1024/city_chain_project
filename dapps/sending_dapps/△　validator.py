# validator.py
"""
validator.py

このモジュールは、生成されたトランザクションの整合性検証を行います。
トランザクション生成時に固定された freeze_hash と、再計算したハッシュを比較します。
"""

import json
import hashlib

def validate_transaction(transaction):
    fixed_hash = transaction.get("freeze_hash")
    data_for_hash = transaction.copy()
    data_for_hash.pop("freeze_hash", None)
    recalculated_hash = hashlib.sha256(json.dumps(data_for_hash, sort_keys=True).encode()).hexdigest()
    return fixed_hash == recalculated_hash

if __name__ == "__main__":
    sample = {"a": 1, "b": 2}
    sample["freeze_hash"] = hashlib.sha256(json.dumps(sample, sort_keys=True).encode()).hexdigest()
    print(validate_transaction(sample))
