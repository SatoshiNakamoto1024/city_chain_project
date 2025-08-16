# dapps/sending_dapps/__init__.py

from flask import Blueprint

# Blueprint を外から import できるように
from .sending_dapps import send_bp  # noqa:F401

__all__ = ["send_bp"]
