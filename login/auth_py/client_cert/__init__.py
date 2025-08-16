"""
auth_py.client_cert パッケージ公開口
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from auth_py.client_cert.app_client_cert import generate_client_keys_interface

__all__: list[str] = [
    "generate_client_keys_interface",
]
