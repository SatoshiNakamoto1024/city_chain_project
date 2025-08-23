//sending_DAG/rust_sending/dag_core/src/object_dependency.rs
// 主な変更点
// object_map: “owned, shared, immutable” の概念を導入
// Txごとに read_set, write_set。
// 所有権チェック
// “owned” object → tx.sender == owner でなければInvalid
// “immutable” → write_set で書き込みしようとするとInvalid
// “shared” → OKだが同時書き込みは衝突
// 16シャード → shard_of(object_id)
// シャード間の衝突判定 → “write overlap” として簡略化
// （本当にSui風にするなら read/write区分をさらに厳密に区別し read_shards vs write_shards で衝突条件を細分化するとより正確）
// トポロジカルソート → サイクルがあればConflict
// cycleノードをReject, それ以外をAccept

// D:\city_chain_project\network\DAGs\rust\src\object_dependency.rs

/*!
object_dependency.rs (Suiレベル風：read/write区分 + Owned/Shared/Immutable + 16シャード + トポロジカルソート)

■ 主なロジック:
1) 各Txのread_set/write_setとsenderを確認:
   - Owned(Owner)オブジェクトにwriteするならTx.sender == Ownerか検証
   - ImmutableにwriteはInvalid
   - Sharedに複数Txがread/writeする場合の衝突を判定
2) 16シャード: object_id => shard_of(object_id) = (SHA256(obj_id)[0] & 0x0f)
3) 衝突:
   - read/read => 衝突なし (ただしimmutableは制限なし, Owned/SharedのreadもOK)
   - read/write => 衝突 if object is Shared or Owned(他人)
   - write/write => 衝突 if same object is Shared, or Owned(同じuser or他ユーザ). (本例では複数Txが1 Owned objectを書こうとすると衝突扱い)
4) トポロジカルソート:
   - i<j => i->j if衝突
   - cycle => そこに含まれるTxをReject
   - cycle外 => Accept
*/

use serde::{Deserialize, Serialize};
use std::collections::{HashSet, HashMap, VecDeque};
use sha2::{Sha256, Digest};

/// オブジェクトの所有形態
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ObjectType {
    Owned(String),   // 所有者
    Shared,
    Immutable,
}

/// Python側から受け取るトランザクション構造
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObjDepTx {
    pub tx_id: String,
    pub sender: String,       // Tx送信者
    pub hash: String,         // 署名ハッシュなど
    pub read_set: Vec<String>,
    pub write_set: Vec<String>,
}

/// 検証結果 (Txごと)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ResolveStatus {
    Success,
    Conflict(String),
    Invalid(String),   // 所有権違反, Immutableへwrite, etc
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResolvedTx {
    pub tx: ObjDepTx,
    pub status: ResolveStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResolveResult {
    pub accepted: Vec<ResolvedTx>,
    pub rejected: Vec<ResolvedTx>,
}

/// object_id => ObjectType
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObjectMap {
    pub mapping: HashMap<String, ObjectType>,
}

/// shard計算 => 0..15
fn shard_of(obj_id: &str) -> u8 {
    let mut hasher = Sha256::new();
    hasher.update(obj_id.as_bytes());
    let res = hasher.finalize();
    let b = res[0];
    b & 0x0f
}

/// Suiレベル風衝突解決
pub fn resolve_object_dependencies(
    tx_list: Vec<ObjDepTx>,
    obj_map: ObjectMap
) -> ResolveResult {
    // まず Invalid判定(所有権, immutable書き込み等)
    let mut invalid_txs = Vec::new();
    let mut valid_txs = Vec::new();

    for tx in &tx_list {
        let mut reason = String::new();
        let mut is_invalid = false;
        // check write_set
        for wobj in &tx.write_set {
            match obj_map.mapping.get(wobj) {
                Some(ObjectType::Owned(owner)) => {
                    if &tx.sender != owner {
                        is_invalid = true;
                        reason = format!("Tx {} tries to write Owned({}), but sender={}", tx.tx_id, owner, tx.sender);
                        break;
                    }
                    // 同一ユーザが書く => OK => ただし衝突は後で判定
                }
                Some(ObjectType::Shared) => {
                    // shared => read/write衝突は後で判定
                }
                Some(ObjectType::Immutable) => {
                    // immutableにwrite => invalid
                    is_invalid = true;
                    reason = format!("Tx {} tries to write Immutable obj {}", tx.tx_id, wobj);
                    break;
                }
                None => {
                    // obj not found => invalid?
                    is_invalid = true;
                    reason = format!("Tx {}: object {} not found", tx.tx_id, wobj);
                    break;
                }
            }
        }
        if is_invalid {
            invalid_txs.push((tx.clone(), reason));
        } else {
            valid_txs.push(tx.clone());
        }
    }

    let mut rejected = Vec::new();
    for (itx, rsn) in invalid_txs {
        let rtx = ResolvedTx {
            tx: itx,
            status: ResolveStatus::Invalid(rsn),
        };
        rejected.push(rtx);
    }

    // 次にシャード判定
    // read_shards / write_shards で分ける
    // => read/readは衝突なし, read/writeは衝突(Shared or Owned(別ユーザ?)), write/writeは衝突
    let n = valid_txs.len();
    let mut read_shards = vec![HashSet::new(); n];
    let mut write_shards = vec![HashSet::new(); n];

    // for conflict detail => we store (obj_id -> read or write)
    // ここでは shard区分だけ持つ簡易化
    for (i, tx) in valid_txs.iter().enumerate() {
        // read
        for ro in &tx.read_set {
            // Owned(同じsender) vs Shared? => ここで区別するなら詳細データ持つ
            // 今回は shardに入れるだけ
            read_shards[i].insert(shard_of(ro));
        }
        // write
        for wo in &tx.write_set {
            write_shards[i].insert(shard_of(wo));
        }
    }

    // TxをIDソート
    let mut indexed: Vec<(usize, &ObjDepTx)> = valid_txs.iter().enumerate().collect();
    indexed.sort_by_key(|(_, tx)| tx.tx_id.clone());
    let mut new2old = Vec::with_capacity(n);
    let mut new_read = Vec::with_capacity(n);
    let mut new_write = Vec::with_capacity(n);

    for (new_i, (old_i, tx)) in indexed.iter().enumerate() {
        new2old.push(*old_i);
        new_read.push(read_shards[*old_i].clone());
        new_write.push(write_shards[*old_i].clone());
    }

    let mut adj = vec![Vec::new(); n];
    let mut indeg = vec![0; n];

    // 衝突ルール(簡易Sui):
    // - read/read => no conflict
    // - read/write => conflict if object is Shared or Owned(別オーナー)
    //   => ただし簡略化: "if there's an overlap in write_shards of i & read_shards of j => conflict"
    // - write/write => conflict if overlap
    // - Owned(同一ユーザが同じobjに書く) => ここでは “衝突あり” とする(先着順で実行)
    // => 実装はshard overlap + check if "same user" => skip?
    //   が複雑になるため、ここで全Txについて "sender" が違う or even same => we unify approach "overlap => conflict"

    for i in 0..n {
        let (i_idx, i_tx) = indexed[i];
        for j in (i+1)..n {
            let (j_idx, j_tx) = indexed[j];
            let conflict = is_conflict_sui(
                &new_read[i], &new_write[i],
                &new_read[j], &new_write[j],
                &valid_txs[i_idx],
                &valid_txs[j_idx],
                &obj_map
            );
            if conflict {
                // i->j
                adj[i].push(j);
                indeg[j] += 1;
            }
        }
    }

    // トポロジカルソート
    use std::collections::VecDeque;
    let mut queue = VecDeque::new();
    for i in 0..n {
        if indeg[i] == 0 {
            queue.push_back(i);
        }
    }

    let mut order = Vec::new();
    while let Some(u) = queue.pop_front() {
        order.push(u);
        for &v in &adj[u] {
            indeg[v] -= 1;
            if indeg[v] == 0 {
                queue.push_back(v);
            }
        }
    }

    let cyc = (order.len() < n);
    let mut accepted = Vec::new();
    let mut more_reject = Vec::new();
    if cyc {
        let valid_set: std::collections::HashSet<usize> = order.iter().copied().collect();
        for i in 0..n {
            if valid_set.contains(&i) {
                let old_idx = new2old[i];
                let txo = valid_txs[old_idx].clone();
                accepted.push(ResolvedTx {
                    tx: txo,
                    status: ResolveStatus::Success,
                });
            } else {
                let old_idx = new2old[i];
                let txo = valid_txs[old_idx].clone();
                more_reject.push(ResolvedTx {
                    tx: txo,
                    status: ResolveStatus::Conflict("Cycle in DAG concurrency".into()),
                });
            }
        }
    } else {
        for &x in &order {
            let old_idx = new2old[x];
            let txo = valid_txs[old_idx].clone();
            accepted.push(ResolvedTx {
                tx: txo,
                status: ResolveStatus::Success,
            });
        }
    }

    let mut rejected = rejected;
    rejected.extend(more_reject);

    ResolveResult {
        accepted,
        rejected,
    }
}

//-----------------------------------
// 衝突判定関数: i->j edge?
//-----------------------------------
fn is_conflict_sui(
    i_read: &HashSet<u8>,
    i_write: &HashSet<u8>,
    j_read: &HashSet<u8>,
    j_write: &HashSet<u8>,
    txi: &ObjDepTx,
    txj: &ObjDepTx,
    obj_map: &ObjectMap
) -> bool {
    // 大雑把: shard overlap => possible conflict.
    // しかし read/read => no conflict.
    // なので "if i_write & j_write != ∅ => conflict" (write/write)
    //          "if i_write & j_read != ∅ => conflict" (read/write)
    //  etc.
    // さらに Owned/Shared/Immutableの詳細
    // ここでは shard overlap があれば一旦判定 => そのobjectごとの詳細を見る

    // 1) quick check: if (i_write union i_read) ∩ (j_write union j_read) = ∅ => no conflict
    //   => no shard overlap => no conflict
    let i_all: HashSet<u8> = i_read.union(&i_write).copied().collect();
    let j_all: HashSet<u8> = j_read.union(&j_write).copied().collect();
    if i_all.is_disjoint(&j_all) {
        return false;
    }

    // 2) shard overlap => check each object in detail
    //    => if read/read => no conflict
    //    => if read/write => conflict if "Shared" or "Owned(different user)"
    //    => if write/write => conflict if "Shared" or "Owned(ANY user -> we define conflict for same user too)"

    // collect all object_ids possibly in conflict = union of (i.read_set + i.write_set) ∩ (j.read_set + j.write_set)
    let i_objs: Vec<&str> = txi.read_set.iter().chain(txi.write_set.iter()).map(|s| s.as_str()).collect();
    let j_objs: Vec<&str> = txj.read_set.iter().chain(txj.write_set.iter()).map(|s| s.as_str()).collect();

    // set for i
    use std::collections::HashSet as StdHashSet;
    let i_objset: StdHashSet<&str> = i_objs.into_iter().collect();
    let j_objset: StdHashSet<&str> = j_objs.into_iter().collect();
    let intersection: Vec<&&str> = i_objset.intersection(&j_objset).collect();
    if intersection.is_empty() {
        return false;
    }

    // check each object in intersection
    for &obj in intersection {
        // read/write classification
        let i_reading = txi.read_set.contains(&obj.to_string());
        let i_writing = txi.write_set.contains(&obj.to_string());
        let j_reading = txj.read_set.contains(&obj.to_string());
        let j_writing = txj.write_set.contains(&obj.to_string());

        if let Some(otype) = obj_map.mapping.get(*obj) {
            match otype {
                ObjectType::Immutable => {
                    // read/write => invalid => should have been marked Invalid earlier
                    // read/read => no conflict
                    // => no conflict for read
                    // => if someone wrote => invalid => already out
                    continue;
                }
                ObjectType::Owned(owner) => {
                    // if either Tx's sender != owner => that Tx is Invalid => done above
                    // => so now both are same user or we skip
                    // write/write => we define it as conflict even if same user => to require ordering
                    // read/write => conflict if different Tx => Sui typically sees "1 writer => no parallel read"
                    if i_writing && j_writing {
                        return true;
                    }
                    if (i_writing && j_reading) || (i_reading && j_writing) {
                        return true;
                    }
                }
                ObjectType::Shared => {
                    // read/read => no conflict
                    // read/write => conflict
                    // write/write => conflict
                    if i_writing && j_writing {
                        return true;
                    }
                    if i_writing && j_reading {
                        return true;
                    }
                    if i_reading && j_writing {
                        return true;
                    }
                }
            }
        } else {
            // obj not found => presumably invalid earlier => skip
            continue;
        }
    }

    false
}
