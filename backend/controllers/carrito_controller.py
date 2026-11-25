# Carrito de compras del usuario autenticado (RF-12 a RF-15).
#
# Rol: cliente (el administrador pasa la comprobación de rol, pero solo usa
# SU carrito). Todas las operaciones devuelven el carrito completo
# recalculado para que el frontend actualice la vista con una sola respuesta.
# Contratos: backend/API.md §7.
from flask import Blueprint, jsonify, request

from middleware.auth import requiere_rol, usuario_actual
from models.usuario import CLIENTE
from services import carrito_service

carrito_bp = Blueprint("carrito", __name__, url_prefix="/api/carrito")


def _respuesta(carrito, status_code=200):
    return jsonify({"carrito": carrito.to_dict()}), status_code


@carrito_bp.route("", methods=["GET"])
@requiere_rol(CLIENTE)
def consultar_carrito():
    return _respuesta(carrito_service.obtener_carrito(usuario_actual().id_usuario))


@carrito_bp.route("/items", methods=["POST"])
@requiere_rol(CLIENTE)
def agregar_item():
    carrito = carrito_service.agregar_item(usuario_actual().id_usuario, request.get_json(silent=True))
    return _respuesta(carrito)


@carrito_bp.route("/items/<int:id_detalle_carrito>", methods=["PATCH"])
@requiere_rol(CLIENTE)
def actualizar_cantidad(id_detalle_carrito):
    carrito = carrito_service.actualizar_cantidad(
        usuario_actual().id_usuario, id_detalle_carrito, request.get_json(silent=True)
    )
    return _respuesta(carrito)


@carrito_bp.route("/items/<int:id_detalle_carrito>", methods=["DELETE"])
@requiere_rol(CLIENTE)
def retirar_item(id_detalle_carrito):
    # Borrado lógico de la línea (activo = false); no se ejecuta DELETE en SQL.
    return _respuesta(carrito_service.retirar_item(usuario_actual().id_usuario, id_detalle_carrito))
