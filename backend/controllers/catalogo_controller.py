# Endpoints REST de la página principal y catálogo.
#
# ESTADO: en desarrollo local. Estos endpoints REQUIEREN autenticación
# obligatoria (cualquier rol autenticado) antes de considerarse terminados.
# En la etapa de autenticación se protegerán con el decorador de
# middleware/auth.py. Mientras tanto, create_app() NO registra este
# blueprint en producción.
#
# Los controladores validan parámetros y delegan en la capa de servicios.
# Los errores se convierten en JSON en middleware/error_handlers.py.
from flask import Blueprint, current_app, jsonify

from controllers.parametros import entero_positivo, texto_opcional
from services import catalogo_service

catalogo_bp = Blueprint("catalogo", __name__, url_prefix="/api")


def _tamano_pagina():
    return entero_positivo(
        "por_pagina",
        predeterminado=current_app.config["PAGINA_TAMANO_PREDETERMINADO"],
        maximo=current_app.config["PAGINA_TAMANO_MAXIMO"],
    )


@catalogo_bp.route("/principal", methods=["GET"])
def cargar_pagina_principal():
    datos = catalogo_service.obtener_pagina_principal(por_pagina=_tamano_pagina())
    return jsonify(datos), 200


@catalogo_bp.route("/productos", methods=["GET"])
def buscar_y_filtrar_productos():
    id_categoria = entero_positivo("categoria")
    busqueda = texto_opcional("busqueda", current_app.config["BUSQUEDA_LONGITUD_MAXIMA"])
    pagina = entero_positivo("pagina", predeterminado=1, maximo=10_000)

    datos = catalogo_service.buscar_productos(
        id_categoria=id_categoria,
        busqueda=busqueda,
        pagina=pagina,
        por_pagina=_tamano_pagina(),
    )
    return jsonify(datos), 200


@catalogo_bp.route("/productos/<int:id_producto>", methods=["GET"])
def ver_detalle_producto(id_producto):
    producto = catalogo_service.obtener_detalle_producto(id_producto)
    return jsonify(producto), 200
