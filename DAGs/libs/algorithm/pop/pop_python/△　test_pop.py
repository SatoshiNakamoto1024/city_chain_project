# D:\city_chain_project\Algorithm\PoP\pop_python\test_pop.py
# -*- coding: utf-8 -*-
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pop_python.manager import get_place_info_and_bonus, initialize_pop_system
from pop_python.polygons import load_city_polygons, find_city_by_location


def test_find_city_by_location_direct():
    load_city_polygons()
    assert find_city_by_location(36.5720, 136.6460) == "kanazawa"
    assert find_city_by_location(48.8600, 2.3370)    == "paris"
    assert find_city_by_location(0.0, 0.0) is None


def test_get_place_info_and_bonus_user_provided():
    initialize_pop_system()
    info = get_place_info_and_bonus("user1", 36.5720, 136.6460)
    assert info["city_id"]     == "kanazawa"
    assert pytest.approx(info["multiplier"]) == 1.0
    assert info["method"]      == "UserProvided"


def test_get_place_info_and_bonus_random(monkeypatch):
    monkeypatch.setattr("pop_python.localization.random.uniform", lambda a, b: 0.0)
    initialize_pop_system()
    info = get_place_info_and_bonus("user2")
    assert info["city_id"] is None
    assert pytest.approx(info["multiplier"]) == 1.0
    assert info["method"]      == "MockRandom"
