# D:\city_chain_project\Algolithm\DPoS\dpos_python\dpos_election.py
# dpos_election.py に詳細な総合評価ロジックを追加し、SCORING_CONFIG で各指標のウェイト管理
# compute_eval_score(...) で指標を合計し、ステーク量(AdvancedDPoS)もボーナス加算
# Representative にeval_score とstake_amount を保存
# candidates = [{"rep_id":"R1", "metrics":{...}}] の metrics をdpos_election.pick_representatives に渡す
# これによりアクセス率 / メモリ容量 / 帯域 / uptime / エラー率 / stake などを総合した代表者を選定

"""
dpos_election.py (詳細な総合評価ロジックを組み込み)

- SCORING_CONFIG に各指標のウエイトを定義
- compute_eval_score(metrics) で、アクセス率 / メモリ容量 / harmony_score(和記) / 帯域幅 / 稼働時間(uptime) / エラー率 などを加味
- Advanced DPoS (dpos_advanced) のステーク量もボーナス加点
- pick_representatives(...) / refresh_representatives(...) は既存の仕組みを流用
"""

import time
from . import dpos_advanced


# 指標とそのウエイトを定義
# 例: {"access_rate":0.2,"mem_capacity":0.2,"harmony_score":0.2,"bandwidth":0.15,"uptime":0.15,"error_rate":-0.1}
# 負のウエイト => 低いほど良い(エラー率の場合)、計算時に (1 - error_rate)* weight など工夫も可
SCORING_CONFIG = {
    "access_rate": 0.2,     # 0~1 (高いほど良い)
    "mem_capacity": 0.0005, # GB -> スコアへの変換係数
    "harmony_score": 0.2,   # 0~1 (和記)
    "bandwidth": 0.15,      # float (MB/s) 
    "uptime": 0.15,         # 0~1
    "error_rate": -0.1      # 0~1 (低いほど良い => negative weight)
}

class Representative:
    def __init__(self, rep_id, region_type, region_id, eval_score, stake_amount=0):
        """
        rep_id: 代表者ID
        region_type: "municipality"/"continent"/"global"
        region_id: e.g. "CityA"/"Asia"/"Earth"
        eval_score: 総合評価(0~∞)
        stake_amount: DPoSでロック中のステーク
        """
        self.rep_id = rep_id
        self.region_type = region_type
        self.region_id = region_id
        self.eval_score = eval_score
        self.stake_amount = stake_amount
        self.active = True
        self.term_start = time.time()
        self.term_end = self.term_start + (3 * 30 * 24 * 3600)  # 3ヶ月
        self.earning_token = 0.0

    def __repr__(self):
        return f"<Rep {self.rep_id} {self.region_id} score={self.eval_score:.2f} stake={self.stake_amount:.1f}>"


def compute_eval_score(metrics: dict, adv_manager: dpos_advanced.AdvancedDPoSManager=None, rep_id:str=None) -> float:
    """
    metrics: {
       "access_rate": float(0~1),
       "mem_capacity": float(GB),
       "harmony_score": float(0~1),
       "bandwidth": float(MBps),
       "uptime": float(0~1),
       "error_rate": float(0~1),  # 0に近いほど良い
       ... etc
    }

    SCORING_CONFIGに基づきウエイトをかけて合計。
    さらに adv_manager があれば rep_idの stake量をボーナス加算
    """
    score = 0.0

    # 1) 各指標にウエイトをかける
    for key, weight in SCORING_CONFIG.items():
        val = metrics.get(key, 0.0)
        if key=="error_rate":
            # error_rate は 0が最良 => 1-val を計算し weightをかける
            # 例: weight=-0.1 => score += (1 - error_rate)*(-0.1)? or simpler
            # ここでは "score += (1 - val) * abs(weight)" など
            # 例: (1-err)*0.1
            # ただし negativeにする場合 => いろいろパターン
            # 単純化: score += (1 - val)*abs(weight)
            add_val = (1.0 - val) * abs(weight)
            score += add_val
        else:
            # 正のweight => val * weight
            add_val = val * weight
            score += add_val

    # 2) mem_capacity => 例: SCORING_CONFIG["mem_capacity"] = 0.0005 => 100GB => +0.05
    #    bandwidth => weight=0.15 => 10MB/s => +1.5 => なるかも => 柔軟に調整

    # 3) stakeボーナス (例: stake/10 => 100 => +10?) => ここは本番要件に合わせて
    if adv_manager and rep_id:
        st = adv_manager.get_stake(rep_id)
        # 例: stake_bonus = min(st/100, 2.0)
        stake_bonus = min(st/100.0, 2.0)
        score += stake_bonus

    return max(score,0.0)


def pick_representatives(region_type, region_id, candidates, num_reps=3, adv_manager=None):
    """
    candidates: [ {"rep_id":"R1","metrics":{...}}, ... ]
    => compute_eval_score => sort => pick top
    => return [Representative, ...]
    """
    scored=[]
    for c in candidates:
        rep_id=c["rep_id"]
        s = compute_eval_score(c["metrics"], adv_manager, rep_id)
        # if adv_manager => stake is read inside compute_eval_score
        scored.append((s, rep_id))

    scored.sort(key=lambda x:x[0], reverse=True)
    out=[]
    for i in range(min(num_reps,len(scored))):
        s_val, rid= scored[i]
        stake_val=0.0
        if adv_manager:
            stake_val= adv_manager.get_stake(rid)
        r=Representative(
            rep_id=rid,
            region_type=region_type,
            region_id=region_id,
            eval_score=s_val,
            stake_amount=stake_val
        )
        out.append(r)
    return out

def refresh_representatives(current_list, region_type, region_id, candidates, num_reps=3, adv_manager=None):
    """
    任期/active状態チェック => update
    pick new => merge
    """
    now=time.time()
    kept=[]
    for r in current_list:
        if r.region_type==region_type and r.region_id==region_id:
            if now>r.term_end or not r.active:
                # retire
                continue
            kept.append(r)
        else:
            kept.append(r)
    # pick new
    new_picks= pick_representatives(region_type, region_id, candidates, num_reps, adv_manager)
    kept.extend(new_picks)
    return kept
