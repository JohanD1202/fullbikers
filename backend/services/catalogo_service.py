"""Casos de uso del catálogo.

El servicio obtiene la conexión del pool, coordina los DAO y arma la
respuesta. Las consultas del catálogo son de solo lectura: no necesitan una
transacción explícita (ver config/database.py).
"""
import math

from config import database
from dao.producto_dao import ProductoDAO
from exceptions import RecursoNoEncontradoError


def _paginacion(total, pagina, por_pagina):
    return {
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total_paginas": math.ceil(total / por_pagina) if total else 0,
    }


def obtener_pagina_principal(por_pagina):
    """Categorías activas y la primera página de productos visibles."""
    with database.obtener_conexion() as conn:
        categorias = ProductoDAO.obtener_categorias_activas(conn)
        total = ProductoDAO.contar_catalogo(conn)
        productos = ProductoDAO.listar_catalogo(conn, limite=por_pagina, desplazamiento=0)
    return {
        "categorias": categorias,
        "productos": productos,
        "total_productos": total,
        **_paginacion(total, 1, por_pagina),
    }


def buscar_productos(id_categoria, busqueda, pagina, por_pagina):
    """Productos visibles filtrados por categoría y/o texto, paginados."""
    with database.obtener_conexion() as conn:
        total = ProductoDAO.contar_catalogo(conn, id_categoria=id_categoria, busqueda=busqueda)
        productos = []
        if total > (pagina - 1) * por_pagina:
            productos = ProductoDAO.listar_catalogo(
                conn,
                id_categoria=id_categoria,
                busqueda=busqueda,
                limite=por_pagina,
                desplazamiento=(pagina - 1) * por_pagina,
            )
    return {
        "productos": productos,
        "total_resultados": total,
        **_paginacion(total, pagina, por_pagina),
    }


def obtener_detalle_producto(id_producto):
    with database.obtener_conexion() as conn:
        producto = ProductoDAO.obtener_detalle_producto(conn, id_producto)
    if not producto:
        raise RecursoNoEncontradoError(
            "El producto solicitado no existe o no está disponible.",
            codigo="producto_no_encontrado",
        )
    return producto
