# D:\city_chain_project\Algolithm\DPoS\dpos_python\dpos_monitor.py

"""
dpos_monitor.py (拡張)

- ダブルサイン監視
- inactivity or contradictory vote => suspicious
- threshold => 代表者をforce_inactive
"""


class DPoSMonitor:
    def __init__(self):
        self.suspicious_map = {}  # rep_id => score
        self.double_sign_records = set()

    def record_incident(self, rep_id, reason):
        old = self.suspicious_map.get(rep_id, 0)
        new = old + 20
        self.suspicious_map[rep_id] = new
        print(f"[DPoSMonitor] inc => rep={rep_id} reas={reason} => suspicious={new}")

    def record_double_sign(self, rep_id, batch_hash):
        """
        2つの異なるvoteで同じbatchに署名 => double sign => suspicious+100
        """
        key = (rep_id, batch_hash)
        if key in self.double_sign_records:
            # second sign => double
            old = self.suspicious_map.get(rep_id, 0)
            new = old + 100
            self.suspicious_map[rep_id] = new
            print(f"[DPoSMonitor] DOUBLE SIGN rep={rep_id}, batch={batch_hash}, suspicious={new}")
        else:
            self.double_sign_records.add(key)

    def check_validity(self, rep, threshold=50):
        sc = self.suspicious_map.get(rep.rep_id, 0)
        if sc >= threshold:
            rep.active = False
            return False
        return True
