# Endpoints técnicos de diagnóstico. Públicos: no exponen información sensible.
from flask import Blueprint, jsonify

from config import database

health_bp = Blueprint("health", __name__, url_prefix="/api/health")


@health_bp.route("", methods=["GET"])
def health_check():
    """Comprueba que Flask responde. No consulta PostgreSQL."""
    return jsonify({"estado": "OK", "servicio": "API FullBikers"}), 200


@health_bp.route("/db", methods=["GET"])
def health_check_db():
    """Ejecuta SELECT 1. Si falla, el manejador de errores responde 503."""
    database.verificar_conexion()
    return jsonify({"estado": "OK", "base_de_datos": "disponible"}), 200
