import pytest

from exceptions import RecursoNoEncontradoError
from services import catalogo_service


@pytest.fixture
def llamadas(monkeypatch):
    """Sustituye el servicio y registra los argumentos recibidos."""
    registro = {}

    def buscar_productos(**kwargs):
        registro["buscar"] = kwargs
        return {"productos": [], "total_resultados": 0, "pagina": kwargs["pagina"],
                "por_pagina": kwargs["por_pagina"], "total_paginas": 0}

    def obtener_pagina_principal(**kwargs):
        registro["principal"] = kwargs
        return {"categorias": [], "productos": [], "total_productos": 0,
                "pagina": 1, "por_pagina": kwargs["por_pagina"], "total_paginas": 0}

    def obtener_detalle_producto(id_producto):
        if id_producto == 999:
            raise RecursoNoEncontradoError("El producto solicitado no existe o no está disponible.",
                                           codigo="producto_no_encontrado")
        return {"id_producto": id_producto, "precio": "1000.00", "variantes": []}

    monkeypatch.setattr(catalogo_service, "buscar_productos", buscar_productos)
    monkeypatch.setattr(catalogo_service, "obtener_pagina_principal", obtener_pagina_principal)
    monkeypatch.setattr(catalogo_service, "obtener_detalle_producto", obtener_detalle_producto)
    return registro


def test_productos_sin_parametros_usa_valores_predeterminados(client, llamadas):
    assert client.get("/api/productos").status_code == 200
    assert llamadas["buscar"] == {"id_categoria": None, "busqueda": None, "pagina": 1, "por_pagina": 12}


def test_productos_pasa_filtros_normalizados(client, llamadas):
    respuesta = client.get("/api/productos?categoria=3&busqueda=%20casco%20&pagina=2&por_pagina=5")
    assert respuesta.status_code == 200
    assert llamadas["buscar"] == {"id_categoria": 3, "busqueda": "casco", "pagina": 2, "por_pagina": 5}


def test_busqueda_vacia_equivale_a_sin_busqueda(client, llamadas):
    client.get("/api/productos?busqueda=%20%20")
    assert llamadas["buscar"]["busqueda"] is None


@pytest.mark.parametrize(
    "consulta, parametro",
    [
        ("categoria=abc", "categoria"),
        ("categoria=0", "categoria"),
        ("categoria=-1", "categoria"),
        ("categoria=99999999999", "categoria"),
        ("pagina=0", "pagina"),
        ("por_pagina=51", "por_pagina"),
        ("por_pagina=1.5", "por_pagina"),
        ("busqueda=" + "a" * 101, "busqueda"),
    ],
)
def test_parametros_invalidos_devuelven_400(client, llamadas, consulta, parametro):
    respuesta = client.get(f"/api/productos?{consulta}")
    assert respuesta.status_code == 400
    error = respuesta.get_json()["error"]
    assert error["codigo"] == "parametro_invalido"
    assert error["detalles"] == {"parametro": parametro}
    assert "buscar" not in llamadas


def test_busqueda_de_100_caracteres_es_valida(client, llamadas):
    assert client.get("/api/productos?busqueda=" + "a" * 100).status_code == 200


def test_principal_acepta_tamano_de_pagina(client, llamadas):
    respuesta = client.get("/api/principal?por_pagina=8")
    assert respuesta.status_code == 200
    assert llamadas["principal"] == {"por_pagina": 8}


def test_detalle_existente(client, llamadas):
    respuesta = client.get("/api/productos/7")
    assert respuesta.status_code == 200
    assert respuesta.get_json()["id_producto"] == 7


def test_detalle_inexistente_devuelve_404_json(client, llamadas):
    respuesta = client.get("/api/productos/999")
    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"]["codigo"] == "producto_no_encontrado"


def test_detalle_con_id_no_numerico_devuelve_404(client, llamadas):
    assert client.get("/api/productos/abc").status_code == 404


def test_catalogo_sin_base_de_datos_devuelve_503(client):
    # Sin sustituir el servicio: la configuración de pruebas no tiene DATABASE_URL.
    respuesta = client.get("/api/productos")
    assert respuesta.status_code == 503
    assert respuesta.get_json()["error"]["codigo"] == "base_de_datos_no_disponible"
