"""
本番では gRPC stub を生成して利用する。
ここでは成功=True を返すダミー。
"""
def send_grpc(target_node_id: str, tx_dict: dict) -> bool:
    print(f"[gRPC] send tx={tx_dict['tx_id']} -> {target_node_id}")
    return True
