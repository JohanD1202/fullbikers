# RF-11: direcciones de entrega del usuario autenticado.
#
# Rol: cliente (el administrador pasa la comprobación de rol, pero solo
# gestiona SUS direcciones: el propietario siempre es el usuario del token).
# Contratos: backend/API.md §6.
from flask import Blueprint, jsonify, request

from middleware.auth import requiere_rol, usuario_actual
from models.usuario import CLIENTE
from services import direccion_service

direccion_bp = Blueprint("direcciones", __name__, url_prefix="/api/direcciones")


def _id_usuario():
    return usuario_actual().id_usuario


@direccion_bp.route("", methods=["GET"])
@requiere_rol(CLIENTE)
def listar_direcciones():
    direcciones = direccion_service.listar(_id_usuario())
    return jsonify({"direcciones": [d.to_dict() for d in direcciones]}), 200


@direccion_bp.route("", methods=["POST"])
@requiere_rol(CLIENTE)
def crear_direccion():
    direccion = direccion_service.crear(_id_usuario(), request.get_json(silent=True))
    return jsonify({"direccion": direccion.to_dict()}), 201


@direccion_bp.route("/<int:id_direccion>", methods=["GET"])
@requiere_rol(CLIENTE)
def obtener_direccion(id_direccion):
    direccion = direccion_service.obtener(_id_usuario(), id_direccion)
    return jsonify({"direccion": direccion.to_dict()}), 200


@direccion_bp.route("/<int:id_direccion>", methods=["PATCH"])
@requiere_rol(CLIENTE)
def actualizar_direccion(id_direccion):
    direccion = direccion_service.actualizar(_id_usuario(), id_direccion, request.get_json(silent=True))
    return jsonify({"direccion": direccion.to_dict()}), 200


@direccion_bp.route("/<int:id_direccion>", methods=["DELETE"])
@requiere_rol(CLIENTE)
def eliminar_direccion(id_direccion):
    # Borrado lógico (activo = false); no se ejecuta DELETE en SQL.
    direccion_service.eliminar(_id_usuario(), id_direccion)
    return "", 204
