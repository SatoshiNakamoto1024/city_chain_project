# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\tests\confetest.py
"""Shared pytest fixtures."""

import asyncio
import pytest

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
