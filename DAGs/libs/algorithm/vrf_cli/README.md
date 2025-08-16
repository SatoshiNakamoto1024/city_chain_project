➕ vrf_cli (2) — CLIツール
役割: 手動検証・Ops用途（鍵生成・prove・verify・ベンチ）。
コマンド例:
vrf-cli keygen --algo bls
vrf-cli prove --algo bls --sk sk.bin --msg hex:01ab...
vrf-cli verify --algo sodium --pk pk.bin --msg hex:... --proof proof.bin