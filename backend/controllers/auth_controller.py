# Endpoints de autenticación (RF-06 a RF-09).
#
# Públicos: POST /api/auth/register (solo clientes) y POST /api/auth/login.
# Autenticados: POST /api/auth/logout y GET /api/auth/me.
# Contratos: backend/API.md §4.
from flask import Blueprint, current_app, jsonify, request

from middleware.auth import requiere_autenticacion, usuario_actual
from services import auth_service
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _cuerpo_json():
    # silent=True: un cuerpo ausente o mal formado llega como None y el
    # servicio responde 400 con el formato de error de la API.
    return request.get_json(silent=True)


@auth_bp.route("/register", methods=["POST"])
def registrar():
    usuario = auth_service.registrar_cliente(_cuerpo_json())
    return jsonify({"usuario": usuario.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def iniciar_sesion():
    token, usuario = auth_service.iniciar_sesion(_cuerpo_json(), request.remote_addr)
    vigencia = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    return jsonify({
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": int(vigencia.total_seconds()),
        "usuario": usuario.to_dict(),
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@requiere_autenticacion
def cerrar_sesion():
    # Sin revocación en el servidor: el frontend elimina el token de
    # sessionStorage. Un token copiado sigue siendo válido hasta expirar.
    return "", 204


@auth_bp.route("/me", methods=["GET"])
@requiere_autenticacion
def usuario_autenticado():
    return jsonify({"usuario": usuario_actual().to_dict()}), 200
