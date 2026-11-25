# RF-10: datos personales del usuario autenticado.
#
# Consulta: GET /api/auth/me (auth_controller.py).
# Actualización: PATCH /api/perfil. Rol del requerimiento: cliente (el
# administrador pasa cualquier comprobación de rol). Cada usuario solo edita
# SU perfil: la identidad sale del token, nunca del cuerpo ni de la URL.
from flask import Blueprint, jsonify, request

from middleware.auth import requiere_rol, usuario_actual
from models.usuario import CLIENTE
from services import perfil_service

perfil_bp = Blueprint("perfil", __name__, url_prefix="/api/perfil")


@perfil_bp.route("", methods=["PATCH"])
@requiere_rol(CLIENTE)
def actualizar_perfil():
    usuario = perfil_service.actualizar_perfil(usuario_actual().id_usuario, request.get_json(silent=True))
    return jsonify({"usuario": usuario.to_dict()}), 200
