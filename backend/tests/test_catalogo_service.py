from contextlib import contextmanager

import pytest

from config import database
from dao.producto_dao import ProductoDAO
from exceptions import RecursoNoEncontradoError
from services import catalogo_service


@pytest.fixture
def conexion(monkeypatch):
    """Sustituye el pool: los DAO reciben un objeto marcador."""
    marcador = object()

    @contextmanager
    def obtener_conexion():
        yield marcador

    monkeypatch.setattr(database, "obtener_conexion", obtener_conexion)
    return marcador


def test_buscar_calcula_paginacion(monkeypatch, conexion):
    recibidos = {}
    monkeypatch.setattr(ProductoDAO, "contar_catalogo", staticmethod(lambda conn, **kw: 25))

    def listar(conn, **kwargs):
        assert conn is conexion
        recibidos.update(kwargs)
        return [{"id_producto": 1}]

    monkeypatch.setattr(ProductoDAO, "listar_catalogo", staticmethod(listar))
    resultado = catalogo_service.buscar_productos(id_categoria=2, busqueda="x", pagina=3, por_pagina=10)
    assert recibidos == {"id_categoria": 2, "busqueda": "x", "limite": 10, "desplazamiento": 20}
    assert resultado["total_resultados"] == 25
    assert resultado["total_paginas"] == 3
    assert resultado["pagina"] == 3


def test_buscar_pagina_fuera_de_rango_no_consulta_listado(monkeypatch, conexion):
    monkeypatch.setattr(ProductoDAO, "contar_catalogo", staticmethod(lambda conn, **kw: 5))

    def listar(conn, **kwargs):
        raise AssertionError("No debe consultarse el listado")

    monkeypatch.setattr(ProductoDAO, "listar_catalogo", staticmethod(listar))
    resultado = catalogo_service.buscar_productos(None, None, pagina=4, por_pagina=5)
    assert resultado["productos"] == []
    assert resultado["total_paginas"] == 1


def test_sin_resultados_total_paginas_es_cero(monkeypatch, conexion):
    monkeypatch.setattr(ProductoDAO, "contar_catalogo", staticmethod(lambda conn, **kw: 0))
    resultado = catalogo_service.buscar_productos(None, "nada", pagina=1, por_pagina=12)
    assert resultado["total_paginas"] == 0 and resultado["productos"] == []


def test_pagina_principal(monkeypatch, conexion):
    monkeypatch.setattr(ProductoDAO, "obtener_categorias_activas", staticmethod(lambda conn: [{"id_categoria": 1}]))
    monkeypatch.setattr(ProductoDAO, "contar_catalogo", staticmethod(lambda conn, **kw: 30))
    monkeypatch.setattr(ProductoDAO, "listar_catalogo", staticmethod(lambda conn, **kw: [{}] * kw["limite"]))
    resultado = catalogo_service.obtener_pagina_principal(por_pagina=12)
    assert resultado["total_productos"] == 30
    assert len(resultado["productos"]) == 12
    assert resultado["total_paginas"] == 3


def test_detalle_inexistente_lanza_404(monkeypatch, conexion):
    monkeypatch.setattr(ProductoDAO, "obtener_detalle_producto", staticmethod(lambda conn, i: None))
    with pytest.raises(RecursoNoEncontradoError):
        catalogo_service.obtener_detalle_producto(5)
