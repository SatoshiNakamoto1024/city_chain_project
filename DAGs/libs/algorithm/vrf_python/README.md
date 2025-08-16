➕ vrf_python (3) — Python専用の薄いPyO3ラッパ
役割: vrf_core + vrf_bls + vrf_libsodium を単一Pythonパッケージとして提供。
API:
from vrf_python import prove, verify, elect_leader  # 実装種別を引数で選択
メリット: Pythonユーザはひとつのpipパッケージで完結。