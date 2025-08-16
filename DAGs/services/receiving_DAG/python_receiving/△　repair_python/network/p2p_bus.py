"""
極簡易 P2P Broadcast (pub-sub) ダミー
"""
subscribers = []

def subscribe(cb):
    subscribers.append(cb)

def broadcast(tx_dict: dict):
    for cb in subscribers:
        cb(tx_dict)
