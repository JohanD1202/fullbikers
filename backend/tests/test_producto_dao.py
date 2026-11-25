"""Pruebas del DAO con una conexión falsa.

Verifican la construcción de las consultas (columnas, filtros, parámetros) y
el mapeo de resultados. NO demuestran que el SQL funcione en PostgreSQL: eso
se comprobará en la verificación de integración contra la rama development.
"""
from decimal import Decimal

import psycopg
import pytest
from psycopg import errors

from dao.producto_dao import ProductoDAO, escapar_patron_like
from tests.conftest import ConexionFalsa


def _fila_producto(**cambios):
    fila = {
        "id_producto": 1, "id_categoria": 2, "categoria_nombre": "Cascos",
        "nombre": "Casco Integral", "referencia": "CAS-001", "descripcion": "Certificado",
        "marca": "Marca", "precio": Decimal("450000.00"), "imagen": None, "activo": True,
        "stock_total": 7,
    }
    fila.update(cambios)
    return fila


def _fila_variante(**cambios):
    fila = {"id_variante": 10, "id_producto": 1, "talla": "M", "color": "Negro",
            "compatibilidad": None, "sku": "CAS-001-M-NEG", "stock": 4, "activo": True}
    fila.update(cambios)
    return fila


def _sql_normalizado(query):
    return " ".join(query.split())


def test_categorias_filtran_por_activo_y_no_usan_estado():
    conn = ConexionFalsa([[{"id_categoria": 1, "nombre": "Cascos", "descripcion": None, "activo": True}]])
    categorias = ProductoDAO.obtener_categorias_activas(conn)
    sql = _sql_normalizado(conn.ejecutadas[0][0])
    assert "WHERE activo" in sql
    assert "estado" not in sql
    assert categorias == [{"id_categoria": 1, "nombre": "Cascos", "descripcion": None, "activo": True}]


def test_listado_solo_considera_productos_categorias_y_variantes_activas():
    conn = ConexionFalsa([[_fila_producto()]])
    ProductoDAO.listar_catalogo(conn)
    sql = _sql_normalizado(conn.ejecutadas[0][0])
    assert "estado" not in sql
    assert "JOIN variante_producto vp ON vp.id_producto = p.id_producto AND vp.activo" in sql
    assert "WHERE p.activo AND c.activo" in sql
    assert "LEFT JOIN" not in sql


def test_listado_parametriza_filtros_y_paginacion():
    conn = ConexionFalsa([[]])
    ProductoDAO.listar_catalogo(conn, id_categoria=3, busqueda="casco", limite=12, desplazamiento=24)
    query, params = conn.ejecutadas[0]
    assert "p.id_categoria = %s" in query
    assert "ILIKE %s" in query
    assert "LIMIT %s OFFSET %s" in query
    assert params == (3, "%casco%", "%casco%", 12, 24)
    assert "casco" not in query


def test_busqueda_escapa_comodines():
    barra = "\\"
    assert escapar_patron_like("50%_off" + barra) == "50" + barra + "%" + barra + "_off" + barra + barra
    conn = ConexionFalsa([{"total": 0}])
    ProductoDAO.contar_catalogo(conn, busqueda="100%")
    _, params = conn.ejecutadas[0]
    patron = "%100" + barra + "%%"
    assert params == (patron, patron)


def test_conteo_usa_los_mismos_filtros_que_el_listado():
    conn = ConexionFalsa([{"total": 5}])
    assert ProductoDAO.contar_catalogo(conn, id_categoria=2) == 5
    sql = _sql_normalizado(conn.ejecutadas[0][0])
    assert sql.startswith("SELECT COUNT(DISTINCT p.id_producto) AS total")
    assert "vp.activo" in sql and "p.id_categoria = %s" in sql


def test_listado_serializa_precio_como_cadena_decimal():
    conn = ConexionFalsa([[_fila_producto(stock_total=0)]])
    producto = ProductoDAO.listar_catalogo(conn)[0]
    assert producto["precio"] == "450000.00"
    assert producto["stock_total"] == 0
    assert producto["disponible"] is False


def test_detalle_solo_incluye_variantes_activas():
    conn = ConexionFalsa([[_fila_producto()], [_fila_variante(), _fila_variante(id_variante=11, sku="X-2", stock=0)]])
    detalle = ProductoDAO.obtener_detalle_producto(conn, 1)
    consulta_variantes = _sql_normalizado(conn.ejecutadas[1][0])
    assert "WHERE id_producto = %s AND activo" in consulta_variantes
    assert conn.ejecutadas[0][1] == (1,)
    assert detalle["stock_total"] == 4
    assert [v["disponible"] for v in detalle["variantes"]] == [True, False]
    assert detalle["precio"] == "450000.00"


def test_detalle_de_producto_no_visible_devuelve_none():
    conn = ConexionFalsa([[]])
    assert ProductoDAO.obtener_detalle_producto(conn, 1) is None


def test_detalle_sin_variantes_activas_devuelve_none():
    conn = ConexionFalsa([[_fila_producto()], []])
    assert ProductoDAO.obtener_detalle_producto(conn, 1) is None


def test_errores_de_postgresql_se_propagan_sin_ocultarse():
    class ConexionQueFalla(ConexionFalsa):
        def cursor(self):
            cursor = super().cursor()

            def execute(query, params=None):
                raise errors.UndefinedColumn("column does not exist")

            cursor.execute = execute
            return cursor

    with pytest.raises(psycopg.Error):
        ProductoDAO.listar_catalogo(ConexionQueFalla())
