"""Integración: consultas reales del catálogo (DAO + servicio) sobre seed_dev.sql.

Valores esperados documentados en database/seed_dev.sql.
"""
from decimal import Decimal

import pytest

from dao.producto_dao import ProductoDAO
from services import catalogo_service

VISIBLES = {
    "CAS-INT-001", "CAS-ABA-002", "CAS-JET-003", "GUA-VER-001", "GUA-INV-002", "CHA-TEX-001",
    "IMP-2PZ-001", "ACC-SOP-001", "ACC-CAN-002", "ACC-MAL-003", "ACC-DEF-004",
}
NO_VISIBLES = ("CHA-CUE-002", "ACC-LUZ-005", "REP-PAS-001")


@pytest.fixture
def ids(conn):
    filas = conn.execute("SELECT referencia, id_producto FROM producto").fetchall()
    return {f["referencia"]: f["id_producto"] for f in filas}


@pytest.fixture
def categorias(conn):
    filas = conn.execute("SELECT nombre, id_categoria FROM categoria").fetchall()
    return {f["nombre"]: f["id_categoria"] for f in filas}


def _referencias(productos):
    return {p["referencia"] for p in productos}


def test_catalogo_solo_productos_visibles(conn):
    assert ProductoDAO.contar_catalogo(conn) == 11
    productos = ProductoDAO.listar_catalogo(conn)
    assert _referencias(productos) == VISIBLES
    ids_orden = [p["id_producto"] for p in productos]
    assert ids_orden == sorted(ids_orden, reverse=True)  # más recientes primero


def test_categorias_activas(conn):
    nombres = [c["nombre"] for c in ProductoDAO.obtener_categorias_activas(conn)]
    assert nombres == sorted(nombres)
    assert {"Accesorios", "Cascos", "Chaquetas", "Guantes", "Impermeables"} <= set(nombres)
    assert "Repuestos" not in nombres


@pytest.mark.parametrize(
    "busqueda, esperadas",
    [
        ("casco", {"CAS-INT-001", "CAS-ABA-002", "CAS-JET-003"}),
        ("CASCO", {"CAS-INT-001", "CAS-ABA-002", "CAS-JET-003"}),
        ("cas-int", {"CAS-INT-001"}),                                    # por referencia
        ("acc-", {"ACC-SOP-001", "ACC-CAN-002", "ACC-MAL-003", "ACC-DEF-004"}),  # sin ACC-LUZ-005
        ("guantes", {"GUA-VER-001", "GUA-INV-002"}),
        ("cuero", set()),                                                # producto inactivo
        ("pastillas", set()),                                            # categoría inactiva
        ("exploradoras", set()),                                         # variantes inactivas
        ("%", set()),                                                    # comodín buscado literal
        ("_", set()),
        ("\\", set()),
    ],
)
def test_busqueda(conn, busqueda, esperadas):
    assert ProductoDAO.contar_catalogo(conn, busqueda=busqueda) == len(esperadas)
    assert _referencias(ProductoDAO.listar_catalogo(conn, busqueda=busqueda)) == esperadas


def test_filtro_por_categoria(conn, categorias):
    cascos = ProductoDAO.listar_catalogo(conn, id_categoria=categorias["Cascos"])
    assert _referencias(cascos) == {"CAS-INT-001", "CAS-ABA-002", "CAS-JET-003"}
    assert ProductoDAO.contar_catalogo(conn, id_categoria=categorias["Accesorios"]) == 4
    assert ProductoDAO.contar_catalogo(conn, id_categoria=categorias["Repuestos"]) == 0
    assert ProductoDAO.contar_catalogo(conn, id_categoria=2_147_483_647) == 0


def test_filtro_y_busqueda_combinados(conn, categorias):
    resultado = ProductoDAO.listar_catalogo(conn, id_categoria=categorias["Cascos"], busqueda="urbano")
    assert _referencias(resultado) == {"CAS-ABA-002"}
    assert ProductoDAO.contar_catalogo(conn, id_categoria=categorias["Guantes"], busqueda="casco") == 0


def test_paginacion_sin_solapamientos(app_bd):
    with app_bd.app_context():
        paginas = [catalogo_service.buscar_productos(None, None, pagina, 5) for pagina in (1, 2, 3, 4)]
    assert [len(p["productos"]) for p in paginas] == [5, 5, 1, 0]
    assert all(p["total_resultados"] == 11 and p["total_paginas"] == 3 for p in paginas)
    vistos = [prod["referencia"] for p in paginas for prod in p["productos"]]
    assert len(vistos) == len(set(vistos)) == 11


def test_pagina_principal(app_bd):
    with app_bd.app_context():
        datos = catalogo_service.obtener_pagina_principal(por_pagina=4)
    assert datos["total_productos"] == 11
    assert len(datos["productos"]) == 4
    assert datos["total_paginas"] == 3


@pytest.mark.parametrize(
    "referencia, stock, disponible",
    [
        ("CAS-INT-001", 13, True),
        ("CAS-ABA-002", 5, True),   # la variante XL inactiva (stock 4) no suma
        ("CAS-JET-003", 0, False),
        ("ACC-CAN-002", 0, False),
        ("ACC-DEF-004", 2, True),
    ],
)
def test_stock_y_disponibilidad(conn, referencia, stock, disponible):
    producto = next(p for p in ProductoDAO.listar_catalogo(conn) if p["referencia"] == referencia)
    assert (producto["stock_total"], producto["disponible"]) == (stock, disponible)


def test_detalle_excluye_variantes_inactivas(conn, ids):
    detalle = ProductoDAO.obtener_detalle_producto(conn, ids["CAS-ABA-002"])
    assert {v["sku"] for v in detalle["variantes"]} == {"CAS-ABA-002-M-BLA", "CAS-ABA-002-L-BLA"}
    assert detalle["stock_total"] == 5


def test_detalle_disponibilidad_por_variante(conn, ids):
    detalle = ProductoDAO.obtener_detalle_producto(conn, ids["CAS-INT-001"])
    por_sku = {v["sku"]: v["disponible"] for v in detalle["variantes"]}
    assert por_sku == {"CAS-INT-001-S-NEG": True, "CAS-INT-001-M-NEG": True, "CAS-INT-001-L-NEG": False}


def test_detalle_variante_base(conn, ids):
    variante = ProductoDAO.obtener_detalle_producto(conn, ids["ACC-SOP-001"])["variantes"][0]
    assert (variante["talla"], variante["color"], variante["compatibilidad"]) == (None, None, None)


@pytest.mark.parametrize("referencia", NO_VISIBLES)
def test_detalle_de_producto_no_visible_es_none(conn, ids, referencia):
    assert ProductoDAO.obtener_detalle_producto(conn, ids[referencia]) is None


def test_detalle_inexistente_es_none(conn):
    assert ProductoDAO.obtener_detalle_producto(conn, 2_147_483_647) is None


def test_precios_exactos(conn, ids):
    fila = conn.execute("SELECT precio FROM producto WHERE referencia = 'CAS-INT-001'").fetchone()
    assert isinstance(fila["precio"], Decimal) and fila["precio"] == Decimal("450000.00")
    precios = {p["referencia"]: p["precio"] for p in ProductoDAO.listar_catalogo(conn)}
    assert precios["CAS-INT-001"] == "450000.00"
    assert precios["GUA-VER-001"] == "85000.00"
    assert ProductoDAO.obtener_detalle_producto(conn, ids["ACC-SOP-001"])["precio"] == "65000.00"
