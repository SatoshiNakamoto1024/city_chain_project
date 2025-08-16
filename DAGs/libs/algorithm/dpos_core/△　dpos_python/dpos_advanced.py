# D:\city_chain_project\Algolithm\DPoS\dpos_python\dpos_advanced.py

"""
dpos_advanced.py

SuiやSolana的な高度機能を取り入れたサンプル。
- stake_lock: 一定期間stakeをロックして安全性確保
- slashing: ダブルサインやサボりを発見したらstakeを減らす
- multi-phase voting (prevote/precommit) => ここはRustで実行するが、Pythonでバリデータ状況を管理

このファイルではPython側でバリデータやステークを管理し、Rustからの通知に応じてslashing/lockを更新。
"""

import time

class StakeInfo:
    def __init__(self, rep_id, amount):
        self.rep_id = rep_id
        self.amount = amount
        self.lock_until = time.time() + 90*24*3600  # 3ヶ月ロック

class AdvancedDPoSManager:
    def __init__(self):
        # rep_id -> StakeInfo
        self.stakes = {}
        # slashed logs
        self.slashed_records = []

    def add_stake(self, rep_id, amount):
        """
        代表者が stake をロックする
        """
        if rep_id in self.stakes:
            self.stakes[rep_id].amount += amount
        else:
            s = StakeInfo(rep_id, amount)
            self.stakes[rep_id] = s
        print(f"[AdvancedDPoS] rep={rep_id} staked={amount}, total={self.stakes[rep_id].amount}")

    def slash(self, rep_id, reason, slash_percent=0.5):
        """
        不正行為があれば stakeを一部or全額スラッシュ(没収)
        """
        if rep_id in self.stakes:
            old_amt = self.stakes[rep_id].amount
            slash_amt = old_amt * slash_percent
            new_amt = old_amt - slash_amt
            self.stakes[rep_id].amount = new_amt
            self.slashed_records.append((rep_id, slash_amt, reason, time.time()))
            print(f"[AdvancedDPoS] SLASH rep={rep_id} reason={reason} slash={slash_amt:.2f} remain={new_amt:.2f}")

    def get_stake(self, rep_id):
        """
        Rust側のバリデータ投票に使う stake
        """
        if rep_id in self.stakes:
            return self.stakes[rep_id].amount
        return 0.0

    def check_lock(self, rep_id):
        """
        lock_until < now => lockが解除
        """
        if rep_id not in self.stakes:
            return True
        now = time.time()
        return (now> self.stakes[rep_id].lock_until)

    def finalize_voting_result(self, batch_hash, result):
        """
        multi-phase => ここではRustで prevote/precommit した最終結果をpythonが受け取り、slashing or reward
        result: { "approved": bool, "bad_validators":[rep_id,...], ... } (想定)
        """
        if not result["approved"]:
            # slashing or partial
            for bad_rep in result.get("bad_validators",[]):
                self.slash(bad_rep, f"BadVoting on {batch_hash}", 0.5)
