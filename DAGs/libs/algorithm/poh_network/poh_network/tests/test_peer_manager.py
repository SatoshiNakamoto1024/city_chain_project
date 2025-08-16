# D:\city_chain_project\DAGs\libs\algorithm\poh_network\poh_network\tests\test_peer_manager.py
import pytest
from poh_network.peer_manager import PeerManager


def test_crud_and_get():
    pm = PeerManager()
    pm.add_peer("grpc", "localhost:50051")
    assert pm.get_peers("grpc") == ["localhost:50051"]
    pm.remove_peer("grpc", "localhost:50051")
    assert pm.get_peers("grpc") == []
