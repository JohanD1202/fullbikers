# Endpoints REST de la página principal y catálogo (RF-01 a RF-05).
#
# Requieren iniciar sesión: no existe catálogo público ni rol visitante.
# Roles: cliente (compra), empleado (consulta productos y variantes para
# verificar pedidos e inventario, RF-29 a RF-34) y administrador (todo).
#
# Los controladores validan parámetros y delegan en la capa de servicios.
# Los errores se convierten en JSON en middleware/error_handlers.py.
from flask import Blueprint, current_app, jsonify

from controllers.parametros import entero_positivo, texto_opcional
from middleware.auth import requiere_rol
from models.usuario import CLIENTE, EMPLEADO
from services import catalogo_service

catalogo_bp = Blueprint("catalogo", __name__, url_prefix="/api")

# El administrador accede siempre (ver middleware/auth.py).
ROLES_CATALOGO = (CLIENTE, EMPLEADO)


def _tamano_pagina():
    return entero_positivo(
        "por_pagina",
        predeterminado=current_app.config["PAGINA_TAMANO_PREDETERMINADO"],
        maximo=current_app.config["PAGINA_TAMANO_MAXIMO"],
    )


@catalogo_bp.route("/principal", methods=["GET"])
@requiere_rol(*ROLES_CATALOGO)
def cargar_pagina_principal():
    datos = catalogo_service.obtener_pagina_principal(por_pagina=_tamano_pagina())
    return jsonify(datos), 200


@catalogo_bp.route("/productos", methods=["GET"])
@requiere_rol(*ROLES_CATALOGO)
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
@requiere_rol(*ROLES_CATALOGO)
def ver_detalle_producto(id_producto):
    producto = catalogo_service.obtener_detalle_producto(id_producto)
    return jsonify(producto), 200
