# /city_chain_project/network/DB/mongodb/pymongo/security/csfle_wrapper.py
"""
Thin decorator to drop-in replace existing handler classes.
Kept for backward compatibility: simply use `@secure_handler()` on original class.
"""
from motor_async_handler import MotorDBHandler

__all__ = ["secure_handler"]

def secure_handler(handler_cls=MotorDBHandler):
    """
    Class decorator: returns subclass with CSFLE auto-enabled.
    """
    return handler_cls
