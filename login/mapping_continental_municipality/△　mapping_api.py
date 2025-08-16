# mapping_continental_municipality/mapping_api.py

from flask import Blueprint, jsonify
from .utils import continents, countries, prefectures, cities

mapping_bp = Blueprint("mapping_bp", __name__, url_prefix="/api/mapping")

@mapping_bp.get("/continents")
def api_continents():
    return jsonify({"continents": continents()})

@mapping_bp.get("/continents/<cont>/countries")
def api_countries(cont):
    return jsonify({"countries": countries(cont)})

@mapping_bp.get("/continents/<cont>/countries/<cntry>/prefectures")
def api_prefs(cont, cntry):
    return jsonify({"prefectures": prefectures(cont, cntry)})

@mapping_bp.get("/continents/<cont>/countries/<cntry>/prefectures/<pref>/cities")
def api_cities(cont, cntry, pref):
    return jsonify({"cities": cities(cont, cntry, pref)})
