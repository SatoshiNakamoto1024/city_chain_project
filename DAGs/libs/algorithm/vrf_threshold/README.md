➕ vrf_threshold (2) — しきい値VRF（BLSベース）
役割: n-of-m の分散鍵で VRF 出力と proof を閾値合成。
API 概略:
pub fn tkeygen(n: usize, t: usize) -> (GroupPk, Vec<PartialSk>);
pub fn partial_prove(psk: &PartialSk, msg: &[u8]) -> PartialProof;
pub fn aggregate(proofs: &[PartialProof]) -> VrfProof;   // t 以上で合成
pub fn verify_group(gpk: &GroupPk, msg: &[u8], proof: &VrfProof) -> bool;
用途: 強い検閲耐性や可用性が要求されるリーダー選出/乱択に最適。