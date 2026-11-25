# Endpoints REST de la página principal y catálogo
from flask import Blueprint, request, jsonify
from dao.producto_dao import ProductoDAO

catalogo_bp = Blueprint("catalogo", __name__, url_prefix="/api")

@catalogo_bp.route("/principal", methods=["GET"])
def cargar_pagina_principal():
    try:
        categorias = ProductoDAO.obtener_categorias_activas()
        productos = ProductoDAO.listar_catalogo()
        return jsonify({
            "categorias": categorias,
            "productos": productos,
            "total_productos": len(productos)
        }), 200
    except Exception:
        return jsonify({"error": "No se pudo cargar la información de la página principal."}), 500

@catalogo_bp.route("/productos", methods=["GET"])
def buscar_y_filtrar_productos():
    id_categoria = request.args.get("categoria", type=int)
    busqueda = request.args.get("busqueda", default="", type=str)

    try:
        productos = ProductoDAO.listar_catalogo(
            id_categoria=id_categoria,
            busqueda=busqueda if busqueda.strip() else None
        )
        return jsonify({
            "productos": productos,
            "total_resultados": len(productos)
        }), 200
    except Exception:
        return jsonify({"error": "Error al consultar los productos."}), 500

@catalogo_bp.route("/productos/<int:id_producto>", methods=["GET"])
def ver_detalle_producto(id_producto):
    try:
        producto = ProductoDAO.obtener_detalle_producto(id_producto)
        if not producto:
            return jsonify({"error": "El producto solicitado no existe o no está disponible."}), 404
        return jsonify(producto), 200
    except Exception:
        return jsonify({"error": "Error al obtener el detalle del producto."}), 500