# Pedidos del usuario autenticado (RF-16 a RF-19).
#
# Rol: cliente (el administrador pasa la comprobación de rol, pero solo
# registra y consulta SUS pedidos; la gestión de pedidos de otros usuarios
# pertenece a RF-32/RF-33). Contratos: backend/API.md §9 y §10.
from flask import Blueprint, jsonify, request

from middleware.auth import requiere_rol, usuario_actual
from models.usuario import CLIENTE
from services import pedido_service

pedido_bp = Blueprint("pedidos", __name__, url_prefix="/api/pedidos")


@pedido_bp.route("", methods=["POST"])
@requiere_rol(CLIENTE)
def registrar_pedido():
    pedido = pedido_service.registrar_pedido(usuario_actual().id_usuario, request.get_json(silent=True))
    return jsonify({"pedido": pedido.to_dict()}), 201


@pedido_bp.route("/<int:id_pedido>", methods=["GET"])
@requiere_rol(CLIENTE)
def obtener_pedido(id_pedido):
    pedido = pedido_service.obtener_pedido(usuario_actual().id_usuario, id_pedido)
    return jsonify({"pedido": pedido.to_dict()}), 200
