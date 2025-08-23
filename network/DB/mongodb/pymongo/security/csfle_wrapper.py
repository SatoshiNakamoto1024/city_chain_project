# /city_chain_project/network/DB/mongodb/pymongo/security/csfle_wrapper.py
"""
Backward-compat decorator stub.
In this minimal production-ready setup, CSFLE is optional and off by default.
If you later enable CSFLE, just make secure_handler() wrap a class that turns it on.
"""
from ..motor_async_handler import MotorDBHandler

__all__ = ["secure_handler"]

def secure_handler(handler_cls=MotorDBHandler):
    """
    Class decorator: returns subclass with CSFLE auto-enabled (stub).
    For now we simply return the handler as-is to keep behavior identical.
    """
    return handler_cls
